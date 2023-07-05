"""Base class for services."""

import dataclasses
import io
from typing import Any, AsyncGenerator, Type

from buzz import require_condition
from fastapi import UploadFile
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.models import Base
from jobbergate_api.storage import search_clause, sort_clause


@dataclasses.dataclass
class TableService:
    """Base class for services containing CRUD operations for tables."""

    db_session: AsyncSession
    base_table: Type[Base]

    async def create(self, **incoming_data) -> Base:
        """Add a new entry to the database."""
        new_entry = self.base_table(**incoming_data)
        self.db_session.add(new_entry)
        await self.db_session.flush()
        await self.db_session.refresh(new_entry)
        return new_entry

    async def count(self) -> int:
        """Count the number of entries on the database."""
        statement = select(func.count()).select_from(self.base_table)
        return (await self.db_session.execute(statement)).scalar_one()

    async def get(self, id_or_identifier: int | str) -> Base:
        """Get an entry by id."""
        query = select(self.base_table)
        query = self._locate_by_id_or_identifier(id_or_identifier, query)
        result = await self.db_session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NoResultFound(f"{self.base_table.__tablename__} with {id_or_identifier=} was not found")
        return row

    async def delete(self, id_or_identifier: int | str) -> None:
        """Delete an entry by id."""
        query = delete(self.base_table)
        query = self._locate_by_id_or_identifier(id_or_identifier, query)
        result = await self.db_session.execute(query)
        if result.rowcount == 0:
            raise NoResultFound(f"{self.base_table.__tablename__} with {id_or_identifier=} was not found")

    async def update(self, id_or_identifier: int | str, **incoming_data) -> Base:
        """Update an entry by id."""
        query = update(self.base_table).returning(self.base_table)
        query = self._locate_by_id_or_identifier(id_or_identifier, query)
        query = query.values(**incoming_data)
        result = await self.db_session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NoResultFound(f"{self.base_table.__tablename__} with {id_or_identifier=} was not found")
        return row

    async def list(
        self,
        search: str | None = None,
        sort_field: str | None = None,
        sort_ascending: bool = True,
        custom_filter=None,
        **kwargs,
    ) -> Page[Base]:
        """List all entries."""
        query = select(self.base_table)
        for key, value in kwargs.items():
            query = query.where(getattr(self.base_table, key) == value)
        if custom_filter:
            query = custom_filter(self.base_table, query)
        if search and hasattr(self.base_table, "searchable_fields"):
            query = query.where(search_clause(search, self.base_table.searchable_fields))
        if sort_field and hasattr(self.base_table, "sortable_fields"):
            query = query.order_by(sort_clause(sort_field, self.base_table.sortable_fields, sort_ascending))
        return await paginate(self.db_session, query)

    def _locate_by_id_or_identifier(self, id_or_identifier: int | str, query):
        if isinstance(id_or_identifier, int):
            target_column = "id"
        elif isinstance(id_or_identifier, str):
            target_column = "identifier"
        else:
            raise TypeError(f"id_or_identifier must be a string or integer, not {type(id_or_identifier)}")

        column = getattr(self.base_table, target_column)

        require_condition(
            column is not None,
            f"{self.base_table.__tablename__} has no column named {target_column}",
            AttributeError,
        )

        return query.where(column == id_or_identifier)


@dataclasses.dataclass
class FileService:
    db_session: AsyncSession
    base_table: Type[Base]
    bucket: Any

    async def file_content_generator(self, entry: Base) -> AsyncGenerator[str, None]:
        """Yield the content of a file to be used with StreamingResponse from FastAPI."""
        file_content = await self.get(entry)
        yield file_content

    async def get(self, entry: Base) -> str:
        """Get the content of a file."""
        s3_object = await self.bucket.Object(entry.file_key)
        response = await s3_object.get()
        file_content = await response["Body"].read()
        return file_content

    async def upsert(self, id: int, upload_content: str | bytes | UploadFile, **incoming_data):
        """Upsert a uploaded content to s3 and the metadata to the corresponding table."""
        template_file = self.base_table(id=id, **incoming_data)

        if isinstance(upload_content, str):
            file_obj: Any = io.BytesIO(upload_content.encode())
        elif isinstance(upload_content, bytes):
            file_obj = io.BytesIO(upload_content)
        elif hasattr(upload_content, "file"):
            file_obj = upload_content.file
        else:
            raise TypeError(f"Unsupported file type {type(upload_content)}")

        await self.bucket.upload_fileobj(Fileobj=file_obj, Key=template_file.file_key)

        merged = await self.db_session.merge(template_file)
        await self.db_session.flush()
        return merged

    async def delete(self, template_file) -> None:
        """Delete a file from s3 and from the corresponding table."""
        await self.db_session.delete(template_file)
        s3_object = await self.bucket.Object(template_file.file_key)
        await s3_object.delete()
        await self.db_session.flush()
