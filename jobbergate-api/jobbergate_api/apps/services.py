"""Provide a generic services for CRUD and file operations in routers."""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Generic, NamedTuple

import httpx
from botocore.response import StreamingBody
from buzz import enforce_defined, handle_errors, require_condition
from fastapi import HTTPException, UploadFile, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from jinja2.exceptions import SecurityError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from loguru import logger
from pydantic import AnyUrl
from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.file_validation import check_uploaded_file_syntax
from jobbergate_api.apps.garbage_collector import GarbageCollector
from jobbergate_api.apps.protocols import CrudModel, FileModel
from jobbergate_api.config import settings
from jobbergate_api.safe_types import Bucket
from jobbergate_api.storage import render_sql, search_clause, sort_clause


class AutoCleanResponse(NamedTuple):
    """
    Named tuple for the response of clean_unused_entries.
    """

    archived: set[int]
    deleted: set[int]


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
            f"{self.name} entry was not found by {locator=}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_404_NOT_FOUND),
        )
        if ensure_attributes:
            self.ensure_attribute(instance, **ensure_attributes)
        return instance

    async def clone_instance(self, original_instance: CrudModel, **incoming_data) -> CrudModel:
        """
        Clone an instance and update it with the supplied data.
        """
        table = self.model_type.__table__  # type: ignore
        non_primary_key_columns = (c.name for c in table.columns if not c.primary_key)
        data = {c: getattr(original_instance, c) for c in non_primary_key_columns}
        data.update(incoming_data)
        data["cloned_from_id"] = original_instance.id

        data.pop("created_at", None)
        data.pop("updated_at", None)

        return await self.create(**data)

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
            f"{self.name} entry was not found by {locator=}",
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
            f"{self.name} entry was not found by {locator=}",
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

        Additional filters can be:
        - Single values: {"status": "ACTIVE"} -> WHERE status = 'ACTIVE'
        - Multiple values (collections): {"status": {"ACTIVE", "DONE"}} -> WHERE status IN ('ACTIVE', 'DONE')
        - Supports lists, tuples, sets: {"status": ["ACTIVE", "DONE"]} -> WHERE status IN ('ACTIVE', 'DONE')
        """
        query = select(self.model_type)
        for key, value in additional_filters.items():
            column = self.model_type.__table__.c[key]  # type: ignore
            if isinstance(value, (set, list, tuple)):
                query = query.where(column.in_(value))
            else:
                query = query.where(column == value)
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
        try:
            logger.trace(f"Query: {render_sql(self.session, query)}")
        except Exception:
            # render_sql might fail with complex query parameters (e.g., sets)
            logger.trace("Query: <complex query - unable to render>")
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
        if mismatched := {k for k, v in attributes.items() if getattr(instance, k) != v}:
            message = f"Mismatch on attribute(s): {', '.join(mismatched)}"
            logger.debug("Access to {} id={} is forbidden due to {}", self.name, instance.id, message)
            raise ServiceError(message, status_code=status.HTTP_403_FORBIDDEN)

    async def clean_unused_entries(self) -> AutoCleanResponse:
        """
        Clean database entries depending on a threshold.
        """
        return AutoCleanResponse(set(), set())

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


class FileService(DatabaseBoundService, BucketBoundService, Generic[FileModel]):
    """
    Provide a service that can perform various file management operations using a supplied ORM model type.
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
        Get a single instance by its parent id and filename (primary keys).

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
        upload_content: str | bytes | AnyUrl | UploadFile | None,
        previous_filename: str | None = None,
        **upsert_kwargs,
    ) -> FileModel:
        """
        Upsert a file instance.

        This method will either create a new file instance or update an existing one.

        If a 'previous_filename' is provided, it is replaced by the new one, being deleted in the process.
        In this case, the 'upload_content' is optional, as the content can be copied from the previous file.
        """
        upsert_instance = await self.add_instance(parent_id, filename, upsert_kwargs)

        if previous_filename == filename:
            previous_filename = None

        if upload_content is not None:
            await self.upload_file_content(upsert_instance, upload_content)
            if not previous_filename:
                return upsert_instance
        if previous_filename:
            previous_instance = await self.get(parent_id, previous_filename)
            if not upload_content:
                await self.copy_file_content(previous_instance, upsert_instance)
            await self.delete(previous_instance)
            return upsert_instance

        raise ServiceError(
            "Either a file or a previous filename must be provided", status_code=status.HTTP_400_BAD_REQUEST
        )

    async def _get_file_data_from_url(self, file_url: AnyUrl) -> io.BytesIO:
        """
        Get file data given a URL.

        Suppports fetching data with the following protocols: http, https, s3
        """
        file_obj = io.BytesIO()
        file_url_string: str

        match file_url.scheme:
            case "s3":
                bucket_name = enforce_defined(
                    file_url.unicode_host(),
                    f"Couldn't extract bucket name from {file_url}",
                    raise_exc_class=ServiceError,
                    raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
                )
                key = enforce_defined(
                    file_url.path,
                    f"Couldn't extract bucket key from {file_url}",
                    raise_exc_class=ServiceError,
                    raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
                )
                file_url_string = f"https://{bucket_name}.s3.amazonaws.com{key}"
            case "http" | "https":
                file_url_string = file_url.unicode_string()
            case _:
                raise ServiceError(f"Unsupported protocol to get file data by url for {file_url}")

        with handle_errors(
            f"Failed to download file from {file_url}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
        ):
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url_string)
                response.raise_for_status()

        file_obj.write(response.content)
        file_obj.seek(0)
        return file_obj

    async def upload_file_content(
        self, instance: FileModel, upload_content: str | bytes | AnyUrl | UploadFile
    ) -> None:
        """
        Upload the content of a file to s3.
        """
        if isinstance(upload_content, str):
            file_obj: Any = io.BytesIO(upload_content.encode())
            size = file_obj.getbuffer().nbytes
        elif isinstance(upload_content, bytes):
            file_obj = io.BytesIO(upload_content)
            size = file_obj.getbuffer().nbytes
        elif isinstance(upload_content, AnyUrl):
            file_obj = await self._get_file_data_from_url(upload_content)
            size = file_obj.getbuffer().nbytes
        elif hasattr(upload_content, "file") and hasattr(upload_content, "size"):
            file_obj = upload_content.file
            size = enforce_defined(
                upload_content.size,  # double checking just because it can be None
                "UploadFile has no size attribute",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        else:
            raise TypeError(f"Unsupported file type {type(upload_content)}")

        require_condition(
            size <= settings.MAX_UPLOAD_FILE_SIZE,
            f"Uploaded files cannot exceed {settings.MAX_UPLOAD_FILE_SIZE} bytes, got {size} bytes",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
        )

        require_condition(
            check_uploaded_file_syntax(file_obj, str(instance.filename)),
            f"File {instance.filename} did not pass the syntax check for its extension",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
        )

        try:
            # Mypy doesn't like aioboto3 much
            await self.bucket.upload_fileobj(Fileobj=file_obj, Key=instance.file_key)  # type: ignore
        except Exception as e:
            message = "Error uploading file {} to {} on bucket {} -- {}".format(
                instance.filename, instance.file_key, self.bucket.name, str(e)
            )
            logger.error(message)
            raise ServiceError(
                f"Error uploading file {instance.filename} to the file storage",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def add_instance(self, parent_id, filename, upsert_kwargs) -> FileModel:
        """
        Add a file instance to the database.
        """
        instance: FileModel = self.model_type(
            parent_id=parent_id,
            filename=filename,
            **upsert_kwargs,
        )
        instance = await self.session.merge(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def clone_instance(self, original_instance: FileModel, new_parent_id: int) -> FileModel:
        """
        Clone a file instance and assign it to a new parent-id.
        """
        logger.info(f"Cloning file={original_instance.file_key} to {new_parent_id=}")
        table = self.model_type.__table__  # type: ignore
        non_primary_key_columns = [c.name for c in table.columns if not c.primary_key]
        data = {c: getattr(original_instance, c) for c in non_primary_key_columns}

        cloned_instance = await self.add_instance(new_parent_id, original_instance.filename, data)

        await self.copy_file_content(original_instance, cloned_instance)
        return cloned_instance

    async def copy_file_content(self, source_instance: FileModel, destination_instance: FileModel) -> None:
        """
        Copy the content of a file from one instance to another.
        """
        copy_source = {"Bucket": self.bucket.name, "Key": source_instance.file_key}
        try:
            await self.bucket.copy(copy_source, destination_instance.file_key)
        except Exception as e:
            message = "Error copying file {} to {} on bucket {} -- {}".format(
                source_instance.file_key, destination_instance.file_key, self.bucket.name, str(e)
            )
            logger.error(message)
            raise ServiceError(
                f"Error copying file {source_instance.file_key} to the file storage",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        with handle_errors(
            f"Unable to process jinja template filename={instance.filename}",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
        ):
            sandbox_env = SandboxedEnvironment()
            template = sandbox_env.from_string(file_content.decode("utf-8"))

        render_contexts = [parameters, {"data": parameters}]

        for context in render_contexts:
            try:
                return template.render(**context)
            except SecurityError as e:
                logger.debug(
                    "Security error rendering filename={} with context={} -- Error: {}",
                    instance.filename,
                    context,
                    str(e),
                )
                raise ServiceError(
                    f"Jinja can not render filename={instance.filename}",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
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

    async def clean_unused_files(self, collector_cls: type[GarbageCollector] = GarbageCollector) -> None:
        """
        Delete unused files from the bucket.

        This method is used to delete files that are not referenced by any row in the database.
        """
        collector = collector_cls(model_type=self.model_type, bucket=self.bucket, session=self.session)
        await collector.run()
