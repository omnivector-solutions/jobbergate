"""Provide a generic services for CRUD and file operations in routers."""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Protocol

from botocore.response import StreamingBody
from buzz import enforce_defined, handle_errors, require_condition
from fastapi import HTTPException, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from jinja2 import Template
from mypy_boto3_s3.service_resource import Bucket
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import Select

from jobbergate_api.storage import search_clause, sort_clause


class ServiceError(HTTPException):
    """
    Make HTTPException more friendly by chaning the default behavior so that the first arg is a message.

    Also needed to play nice with py-buzz methods.
    """

    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        super().__init__(status_code=status_code, detail=message, **kwargs)


class DatabaseBoundService:
    """
    Provide base class for services that bind to a database session.
    """

    _session: AsyncSession | None

    def __init__(self):
        self._session = None

    def bind_session(self, session: AsyncSession):
        self._session = session

    def unbind_session(self):
        self._session = None

    @contextmanager
    def bound_session(self, session: AsyncSession):
        self.bind_session(session)
        try:
            yield self
        finally:
            self.unbind_session()

    @property
    def session(self) -> AsyncSession:
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

    def __init__(self, **kwargs):
        ...

    def __tablename__(self) -> str:
        ...

    @classmethod
    def searchable_fields(cls) -> list[str]:
        ...

    @classmethod
    def sortable_fields(cls) -> list[str]:
        ...


class CrudService(DatabaseBoundService):
    model_type: type[CrudModelProto]

    def __init__(self, model_type: type[CrudModelProto]):
        super().__init__()
        self.model_type = model_type

    async def create(self, **incoming_data) -> CrudModelProto:
        """
        Add a new row for the model to the database.
        """
        instance: CrudModelProto = self.model_type(**incoming_data)

        self.session.add(instance)
        # I think this flush is not necessary
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def count(self) -> int:
        """Count the number of rows in the table on the database."""
        result: Result = await self.session.execute(select(func.count(self.model_type.id)))
        return result.scalar_one()

    async def get(self, locator: Any) -> CrudModelProto:
        """
        Get a row by locator.

        In almost all cases, the locator will just be an ``id`` value.
        """
        query = select(self.model_type).where(self.locate_where_clause(locator))
        result: Result = await self.session.execute(query)
        instance: CrudModelProto = enforce_defined(
            result.scalar_one_or_none(),
            f"{self.model_type.__tablename__} row not found by {locator}",
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
            f"{self.model_type.__tablename__} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )

    async def update(self, locator: Any, **incoming_data) -> CrudModelProto:
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
            f"{self.model_type.__tablename__} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )

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
        **additional_filters,
    ) -> Select:
        """
        Build the query to list matching rows.

        Decomposed into a separate function so that deriving subclasses can add
        additional logic into the query.
        """
        query = select(self.model_type)
        # I'm not sure if this is actually a good idea, but it's cool
        for key, value in additional_filters.items():
            query = query.where(getattr(self.model_type, key) == value)
        if user_email:
            query = query.where(self.model_type.owner_email == user_email)
        if search:
            require_condition(
                hasattr(self.model_type, "searchable_fields"),
                f"{self.model_type.__tablename__} does not support search",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_405_METHOD_NOT_ALLOWED),
            )
            query = query.where(search_clause(search, self.model_type.searchable_fields()))
        if sort_field:
            require_condition(
                hasattr(self.model_type, "sortable_fields"),
                f"{self.model_type.__tablename__} does not support sort",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_405_METHOD_NOT_ALLOWED),
            )
            query = query.order_by(sort_clause(sort_field, self.model_type.sortable_fields(), sort_ascending))
        return query

    async def paginated_list(self, **filter_kwargs) -> Page[CrudModelProto]:
        """
        List all crud rows matching specified filters with pagination.

        For details on the supported filters, see the ``build_list_query()`` method.
        """
        return await paginate(self.session, self.build_list_query(**filter_kwargs))

    async def list(self, **filter_kwargs) -> list[CrudModelProto]:
        """
        List all crud rows matching specified filters.

        For details on the supported filters, see the ``build_list_query()`` method.
        """
        result: Result = await self.session.execute(self.build_list_query(**filter_kwargs))
        return list(result.scalars())


class BucketBoundService:
    """
    Provide base class for services that bind to an s3 bucket.
    """

    _bucket: Bucket | None

    def __init__(self):
        self._bucket = None

    def bind_bucket(self, bucket: Bucket):
        self._bucket = bucket

    def unbind_bucket(self):
        self._bucket = None

    @contextmanager
    def bound_bucket(self, bucket: Bucket):
        self.bind_bucket(bucket)
        try:
            yield self
        finally:
            self.unbind_bucket()

    @property
    def bucket(self) -> Bucket:
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
        ...

    def __tablename__(self) -> str:
        ...


class FileService(DatabaseBoundService, BucketBoundService):
    model_type: type[FileModelProto]

    def __init__(self, model_type: type[FileModelProto]):
        super().__init__()
        self.model_type = model_type

    async def get(self, parent_id: int, filename: str | None = None) -> FileModelProto:
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

    async def find_children(self, parent_id: int) -> list[FileModelProto]:
        """
        Find matching instances by parent_id.
        """
        # Mypy does not like sqlalchemy query chaining
        query = select(self.model_type).where(self.model_type.parent_id == parent_id)  # type: ignore
        result: Result = await self.session.execute(query)
        return list(result.scalars())

    async def stream_file_content(self, instance: FileModelProto) -> StreamingBody:
        """
        Stream the content of a file using a boto3 StreamingBody.

        The StreamingBody is an async generator that can be used for a StreamingResponse in a FastAPI app.
        """
        with handle_errors(
            f"{self.model_type.__tablename__} file content not found for {instance=}",
            handle_exc_class=self.bucket.meta.client.exceptions.NoSuchKey,
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        ):
            # Mypy doesn't like using this approach to getting the object
            file_object = await self.bucket.meta.client.get_object(Bucket=self.bucket.name, Key=instance.file_key)  # type: ignore
        return file_object["Body"]

    async def get_file_content(self, instance: FileModelProto) -> bytes:
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
    ) -> FileModelProto:
        """
        Upsert a file instance.
        """
        instance: FileModelProto = self.model_type(
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

    async def delete(self, instance: FileModelProto) -> None:
        """Delete a file from s3 and from the corresponding table."""
        await self.session.delete(instance)
        # Mypy doesn't like aioboto3 much
        s3_object = await self.bucket.Object(instance.file_key)  # type: ignore
        await s3_object.delete()
        await self.session.flush()

    async def render(self, instance: FileModelProto, parameters: dict[str, Any]) -> str:
        """Render the file using Jinja2."""
        file_content = await self.get_file_content(instance)
        return Template(file_content.decode("utf-8")).render(**parameters)
