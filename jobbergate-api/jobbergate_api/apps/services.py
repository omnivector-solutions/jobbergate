"""Provide a generic services for CRUD and file operations in routers."""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Generic, Protocol, TypeVar

from botocore.response import StreamingBody
from buzz import check_expressions, enforce_defined, handle_errors, require_condition
from fastapi import HTTPException, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from jinja2 import Template
from jinja2.exceptions import UndefinedError
from loguru import logger
from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import Select

from jobbergate_api.safe_types import Bucket
from jobbergate_api.storage import render_sql, search_clause, sort_clause


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

    This class holds a reference to the session and provides methods to bind and unbind the session.
    It also keeps track of all instances of the service so that they can be iterated over.
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
            f"Service {self.__class__.__name__} is not bound to a database session",
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

    @classmethod
    def include_files(cls, query: Select) -> Select:
        """
        Declare that the protocol has a method to include files in a query.
        """
        ...

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Declare that the protocol has a method to include details about the parent entry in a query.
        """
        ...


CrudModel = TypeVar("CrudModel", bound=CrudModelProto)


class CrudService(DatabaseBoundService, Generic[CrudModel]):
    """
    Provide a service that can perform various crud operations using a supplied ORM model type.
    """

    model_type: type[CrudModel]

    def __init__(self, model_type: type[CrudModel]):
        """
        Initialize the instance with an ORM model type.
        """
        super().__init__()
        self.model_type = model_type

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

    async def get(
        self,
        locator: Any,
        include_files: bool = False,
        include_parent: bool = False,
        ensure_attributes: dict[str, Any] | None = None,
    ) -> CrudModel:
        """
        Get a row by locator.

        In almost all cases, the locator will just be an ``id`` value.

        Key value pairs can be provided as ``ensure_attributes`` to assert that the
        key fields have the specified values. This is useful to assert email ownership
        of a row before modifying it, besides any other attribute.
        """
        query = select(self.model_type).where(self.locate_where_clause(locator))
        if include_parent:
            query = self.model_type.include_parent(query)
        if include_files:
            query = self.model_type.include_files(query)
        result: Result = await self.session.execute(query)
        instance: CrudModel = enforce_defined(
            result.unique().scalar_one_or_none(),  # type: ignore
            f"{self.name} row not found by {locator}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )
        if ensure_attributes:
            self.ensure_attribute(instance, **ensure_attributes)
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
            f"{self.name} row not found by {locator=}",
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
            f"{self.name} row not found by {locator=}",
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
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_files: bool = False,
        include_parent: bool = False,
        **additional_filters,
    ) -> Select:
        """
        Build the query to list matching rows.

        Decomposed into a separate function so that deriving subclasses can add
        additional logic into the query.
        """
        query = select(self.model_type)
        for key, value in additional_filters.items():
            query = query.where(self.model_type.__table__.c[key] == value)  # type: ignore
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
        if include_parent:
            query = self.model_type.include_parent(query)
        if include_files:
            query = self.model_type.include_files(query)
        logger.trace(f"Query: {render_sql(self.session, query)}")
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
        return list(result.unique().scalars())  # type: ignore

    def ensure_attribute(self, instance: CrudModel, **attributes) -> None:
        """
        Ensure that a model instance has the specified values on key attributes.

        Raises HTTPException if the instance does not have the specified values.
        """
        with check_expressions(
            main_message="Request not allowed on {} by id={} due to mismatch on attribute(s)".format(
                self.name, instance.id
            ),
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_403_FORBIDDEN),
        ) as check:
            for attr_name, expected_value in attributes.items():
                actual_value = getattr(instance, attr_name)
                check(actual_value == expected_value, message=attr_name)

    @property
    def name(self):
        """
        Helper property to recover the name of the table.
        """
        return self.model_type.__tablename__


class BucketBoundService:
    """
    Provide base class for services that bind to an s3 bucket.

    This class holds a reference to the bucket and provides methods to bind and unbind the bucket.
    It also keeps track of all instances of the service so that they can be iterated over.
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
            f"Service {self.__class__.__name__} is not bound to file storage",
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
        DatabaseBoundService.__init__(self)
        BucketBoundService.__init__(self)
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

        The parameters are passed to the template as the context, and two of them are supported:
        * Directly as the context, for instance, if the template contains ``{{ foo }}``.
        * As a ``data`` key for backward compatibility, for instance, if the
          template contains ``{{ data.foo }}``.

        """
        file_content = await self.get_file_content(instance)
        template = Template(file_content.decode("utf-8"))

        render_contexts = [parameters, {"data": parameters}]

        for context in render_contexts:
            try:
                return template.render(**context)
            except UndefinedError as e:
                logger.debug(
                    "Unable to render filename={} with context={} -- Error: {}",
                    instance.filename,
                    context,
                    str(e),
                )

        raise ServiceError(
            f"Unable to render filename={instance.filename} with the provided parameters",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
