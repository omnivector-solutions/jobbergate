"""Provide a generic services for CRUD and file operations in routers."""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Generic, Protocol, TypeVar

from botocore.response import StreamingBody
from buzz import enforce_defined, handle_errors, require_condition
from fastapi import HTTPException, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from jinja2 import Template
from pydantic import EmailStr
from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, joinedload
from sqlalchemy.sql.expression import Select

from jobbergate_api.safe_types import Bucket
from jobbergate_api.storage import search_clause, sort_clause


class ServiceError(HTTPException):
    """
    Make HTTPException more friendly by changing the default behavior so that the first arg is a message.

    Also needed to play nice with py-buzz methods.
    """

    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        """
        Instantiate the HTTPException super class by setting detail to the message provided.
        """
        super().__init__(status_code=status_code, detail=message, **kwargs)


class DatabaseBoundService:
    """
    Provide base class for services that bind to a database session.
    """

    _session: AsyncSession | None

    def __init__(self):
        """
        Instantiate the service with a null session.
        """
        self._session = None

    def bind_session(self, session: AsyncSession):
        """
        Bind the service to a session.
        """
        self._session = session

    def unbind_session(self):
        """
        Unbind the service from a session.
        """
        self._session = None

    @contextmanager
    def bound_session(self, session: AsyncSession):
        """
        Provide a context within which the service is bound to a session.
        """
        self.bind_session(session)
        try:
            yield self
        finally:
            self.unbind_session()

    @property
    def session(self) -> AsyncSession:
        """
        Fetch the currently bound session.

        Raise an exception if the service is not bound to a session.
        """
        return enforce_defined(
            self._session,
            "Service is not bound to a database session",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_503_SERVICE_UNAVAILABLE),
        )


class CrudModelProto(Protocol):
    """
    Provide a protocol for models that can be operated on by the CrudService.

    This protocol enables type hints for editors and type checking with mypy.

    These services would best be served by an intersection type so that the model_type is actually
    specified to inherit from _both_ the mixins and the Base. This would allow static type checkers to
    recognize that all of the columns in a mixin are available and that the class can be
    instantiated in the create method. However, intersection types are not supported yet. For more
    information, see this discussion: https://github.com/python/typing/issues/213
    """

    id: Mapped[int]
    owner_email: Mapped[str]
    is_archived: Mapped[bool]

    def __init__(self, **kwargs):
        """
        Declare that the protocol can be instantiated.
        """
        ...

    def __tablename__(self) -> str:
        """
        Declare that the protocol has a method to dynamically produce the table name.
        """
        ...

    @classmethod
    def searchable_fields(cls) -> set[str]:
        """
        Declare that the protocol has searchable fields.
        """
        ...

    @classmethod
    def sortable_fields(cls) -> set[str]:
        """
        Declare that the protocol has sortable fields.
        """
        ...


CrudModel = TypeVar("CrudModel", bound=CrudModelProto)


class CrudService(DatabaseBoundService, Generic[CrudModel]):
    """
    Provide a service that can perform various crud operations using a supplied ORM model type.
    """

    model_type: type[CrudModel]
    parent_model_link: Mapped | None

    def __init__(self, model_type: type[CrudModel], parent_model_link: Mapped | None = None):
        """
        Initialize the instance with an ORM model type.
        """
        super().__init__()
        self.model_type = model_type
        self.parent_model_link = parent_model_link

    async def create(self, **incoming_data) -> CrudModel:
        """
        Add a new row for the model to the database.
        """
        instance: CrudModel = self.model_type(**incoming_data)

        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def count(self) -> int:
        """
        Count the number of rows in the table on the database.
        """
        result: Result = await self.session.execute(select(func.count(self.model_type.id)))
        return result.scalar_one()

    async def get(self, locator: Any) -> CrudModel:
        """
        Get a row by locator.

        In almost all cases, the locator will just be an ``id`` value.
        """
        query = select(self.model_type).where(self.locate_where_clause(locator))
        result: Result = await self.session.execute(query)
        instance: CrudModel = enforce_defined(
            result.scalar_one_or_none(),
            f"{self.name} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )
        await self.session.refresh(instance)
        return instance

    async def delete(self, locator: Any) -> None:
        """
        Delete a row by locator.

        In almost all cases, the locator will just be an ``id`` value.
        """
        query = delete(self.model_type).returning(self.model_type).where(self.locate_where_clause(locator))
        result: Result = await self.session.execute(query)
        deleted = list(result.scalars())
        require_condition(
            len(deleted) == 1,
            f"{self.name} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )

    async def update(self, locator: Any, **incoming_data) -> CrudModel:
        """
        Update a row by locator with supplied data.

        In almost all cases, the locator will just be an ``id`` value.
        """
        # Mypy does not like fluent-chained sqlalchemy update queries
        query = (
            update(self.model_type)
            .returning(self.model_type)
            .where(self.locate_where_clause(locator))
            .values(**incoming_data)  # type: ignore
        )
        result: Result = await self.session.execute(query)
        return enforce_defined(
            result.scalar_one_or_none(),
            f"{self.name} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )

    async def get_ensure_ownership(self, locator: Any, requester_email: str | EmailStr | None) -> CrudModel:
        """
        Assert ownership of an entity and raise 403 exception with message on failure.
        """
        enforce_defined(
            requester_email,
            "The token payload does not contain an email",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
        )

        entity = await self.get(locator)

        require_condition(
            entity.owner_email == requester_email,
            (
                f"User {requester_email} does not own {self.name} by {locator}. "
                f"Only the {self.name} owner ({entity.owner_email}) "
                f"can modify this {self.name}."
            ),
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_403_FORBIDDEN),
        )

        return entity

    def locate_where_clause(self, locator: Any) -> Any:
        """
        Provide the where clause expression to locate a row by locator.

        This method allows derived classes to locate by alternative identifiers, though
        locator is an ``id`` value in almost all cases.
        compound primary keys.
        """
        return self.model_type.id == locator

    def build_list_query(
        self,
        sort_ascending: bool = True,
        user_email: str | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        eager_join: bool = False,
        innerjoin: bool = False,
        **additional_filters,
    ) -> Select:
        """
        Build the query to list matching rows.

        Decomposed into a separate function so that deriving subclasses can add
        additional logic into the query.
        """
        query = select(self.model_type)
        for key, value in additional_filters.items():
            query = query.where(getattr(self.model_type, key) == value)
        if user_email:
            query = query.where(self.model_type.owner_email == user_email)
        if not include_archived:
            query = query.where(not_(self.model_type.is_archived))
        if search:
            require_condition(
                hasattr(self.model_type, "searchable_fields"),
                f"{self.name} does not support search",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_405_METHOD_NOT_ALLOWED),
            )
            query = query.where(search_clause(search, self.model_type.searchable_fields()))
        if sort_field:
            require_condition(
                hasattr(self.model_type, "sortable_fields"),
                f"{self.name} does not support sort",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_405_METHOD_NOT_ALLOWED),
            )
            query = query.order_by(sort_clause(sort_field, self.model_type.sortable_fields(), sort_ascending))
        if eager_join and self.parent_model_link is not None:
            query.options(joinedload(self.parent_model_link, innerjoin=innerjoin))
        return query

    async def paginated_list(self, **filter_kwargs) -> Page[CrudModel]:
        """
        List all crud rows matching specified filters with pagination.

        For details on the supported filters, see the ``build_list_query()`` method.
        """
        return await paginate(self.session, self.build_list_query(**filter_kwargs))

    async def list(self, **filter_kwargs) -> list[CrudModel]:
        """
        List all crud rows matching specified filters.

        For details on the supported filters, see the ``build_list_query()`` method.
        """
        result: Result = await self.session.execute(self.build_list_query(**filter_kwargs))
        return list(result.scalars())

    @property
    def name(self):
        """
        Helper property to recover the name of the table.
        """
        return self.model_type.__tablename__


class BucketBoundService:
    """
    Provide base class for services that bind to an s3 bucket.
    """

    _bucket: Bucket | None

    def __init__(self):
        """
        Initialize the service with a null bucket.
        """
        self._bucket = None

    def bind_bucket(self, bucket: Bucket):
        """
        Bind the service to a bucket.
        """
        self._bucket = bucket

    def unbind_bucket(self):
        """
        Unbind the service from a bucket.
        """
        self._bucket = None

    @contextmanager
    def bound_bucket(self, bucket: Bucket):
        """
        Provide a context within which the service is bound to a bucket.
        """
        self.bind_bucket(bucket)
        try:
            yield self
        finally:
            self.unbind_bucket()

    @property
    def bucket(self) -> Bucket:
        """
        Fetch the currently bound bucket.

        Raise an exception if the service is not bound to a bucket.
        """
        return enforce_defined(
            self._bucket,
            "Service is not bound to file storage",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_503_SERVICE_UNAVAILABLE),
        )


class FileModelProto(Protocol):
    """
    Provide a protocol for models that can be operated on by the FileService.

    This protocol enables type hints for editors and type checking with mypy.

    These services would best be served by an intersection type so that the model_type is actually
    specified to inherit from _both_ the mixins and the Base. This would allow static type checkers to
    recognize that all of the columns in a mixin are available and that the class can be
    instantiated in the create method. However, intersection types are not supported yet. For more
    information, see this discussion: https://github.com/python/typing/issues/213
    """

    parent_id: Mapped[int]
    filename: Mapped[str]
    file_key: str

    def __init__(self, **kwargs):
        """
        Declare that the protocol can be instantiated.
        """
        ...

    def __tablename__(self) -> str:
        """
        Declare that the protocol has a method to dynamically produce the table name.
        """
        ...


FileModel = TypeVar("FileModel", bound=FileModelProto)


class FileService(DatabaseBoundService, BucketBoundService, Generic[FileModel]):
    """
    Proide a service that can perform various file management operations using a supplied ORM model type.
    """

    model_type: type[FileModel]

    def __init__(self, model_type: type[FileModel]):
        """
        Initialize the instance with an ORM model type.
        """
        super().__init__()
        self.model_type = model_type

    async def get(self, parent_id: int, filename: str) -> FileModel:
        """
        Get a single instances by its parent id and filename (primary keys).

        Requires that one and only one result is found.
        """
        # Mypy does not like sqlalchemy query chaining
        query = select(self.model_type).where(
            self.model_type.parent_id == parent_id,
            self.model_type.filename == filename,
        )  # type: ignore
        result: Result = await self.session.execute(query)
        return enforce_defined(
            result.scalar_one_or_none(),
            f"{self.model_type.__tablename__} row not found by {parent_id=}, {filename=}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )

    async def find_children(self, parent_id: int) -> list[FileModel]:
        """
        Find matching instances by parent_id.
        """
        # Mypy does not like sqlalchemy query chaining
        query = select(self.model_type).where(self.model_type.parent_id == parent_id)  # type: ignore
        result: Result = await self.session.execute(query)
        return list(result.scalars())

    async def stream_file_content(self, instance: FileModel) -> StreamingBody:
        """
        Stream the content of a file using a boto3 StreamingBody.

        The StreamingBody is an async generator that can be used for a StreamingResponse in a FastAPI app.
        """
        with handle_errors(
            f"{self.model_type.__tablename__} file content not found for {instance=}",
            handle_exc_class=self.bucket.meta.client.exceptions.NoSuchKey,
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR),
        ):
            # Mypy doesn't like aioboto3 much
            s3_object = await self.bucket.Object(instance.file_key)  # type: ignore
            file_object = await s3_object.get()
        return file_object["Body"]

    async def get_file_content(self, instance: FileModel) -> bytes:
        """
        Get the full contents for a file entry.
        """
        stream: StreamingBody = await self.stream_file_content(instance)
        # Mypy doesn't like aioboto3 much
        data: bytes = await stream.read()  # type: ignore
        return data

    async def upsert(
        self,
        parent_id: int,
        filename: str,
        upload_content: str | bytes | UploadFile,
        **upsert_kwargs,
    ) -> FileModel:
        """
        Upsert a file instance.
        """
        instance: FileModel = self.model_type(
            parent_id=parent_id,
            filename=filename,
            **upsert_kwargs,
        )
        instance = await self.session.merge(instance)
        # I'm not sure that this flush is necessary
        await self.session.flush()
        await self.session.refresh(instance)

        if isinstance(upload_content, str):
            file_obj: Any = io.BytesIO(upload_content.encode())
        elif isinstance(upload_content, bytes):
            file_obj = io.BytesIO(upload_content)
        elif hasattr(upload_content, "file"):
            file_obj = upload_content.file
        else:
            raise TypeError(f"Unsupported file type {type(upload_content)}")

        # Mypy doesn't like aioboto3 much
        await self.bucket.upload_fileobj(Fileobj=file_obj, Key=instance.file_key)  # type: ignore
        return instance

    async def delete(self, instance: FileModel) -> None:
        """
        Delete a file from s3 and from the corresponding table.
        """
        await self.session.delete(instance)
        # Mypy doesn't like aioboto3 much
        s3_object = await self.bucket.Object(instance.file_key)  # type: ignore
        await s3_object.delete()
        await self.session.flush()

    async def render(self, instance: FileModel, parameters: dict[str, Any]) -> str:
        """
        Render the file using Jinja2.
        """
        file_content = await self.get_file_content(instance)
        return Template(file_content.decode("utf-8")).render(**parameters)
