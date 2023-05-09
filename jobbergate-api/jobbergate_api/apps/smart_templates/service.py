"""Services for the smart_templates resource, including module specific business logic."""
import dataclasses
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.smart_templates.models import SmartTemplate
from jobbergate_api.apps.smart_templates.schemas import SmartTemplateCreateRequest, SmartTemplateUpdateRequest


@dataclasses.dataclass
class SmartTemplateService:

    session: AsyncSession

    async def create(self, incoming_data: SmartTemplateCreateRequest) -> SmartTemplate:
        """Add a new smart_template to the database."""
        smart_template = SmartTemplate(**incoming_data.dict(exclude_unset=True))
        self.session.add(smart_template)
        await self.session.flush()
        await self.session.refresh(smart_template)
        return smart_template

    async def count(self) -> int:
        """Count the number of smart_templates on the database."""
        result = await self.session.execute(select(func.count(SmartTemplate.id)))
        return result.scalar_one()

    async def get(self, id: int) -> SmartTemplate | None:
        """Get a smart_template by id or identifier."""
        query = select(SmartTemplate)
        query = query.where(SmartTemplate.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> None:
        """Delete a smart_template by id or identifier."""
        job_template = await self.get(id)
        if job_template is None:
            raise NoResultFound("SmartTemplate not found")
        await self.session.delete(job_template)
        await self.session.flush()

    async def update(self, id: int, incoming_data: SmartTemplateUpdateRequest) -> SmartTemplate:
        """Update a job_script_template by id or identifier."""
        query = update(SmartTemplate).returning(SmartTemplate)
        query = query.where(SmartTemplate.id == id)
        query = query.values(**incoming_data.dict(exclude_unset=True))
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one()


@dataclasses.dataclass
class SmartTemplateFilesService:
    """Service for the smart_template_files resource."""

    bucket: Any

    async def get(self, template_file: SmartTemplate):
        """Get a smart_template file."""
        fileobj = await self.bucket.meta.client.get_object(
            Bucket=self.bucket.name, Key=template_file.file_key
        )
        yield fileobj

    async def upsert(self, smart_template: SmartTemplate, upload_file: UploadFile) -> None:
        """Upsert a smart_template file."""
        await self.bucket.upload_fileobj(Fileobj=upload_file.file, Key=smart_template.file_key)

    async def delete(self, smart_template: SmartTemplate) -> None:
        """Delete a smart_template file."""
        await self.bucket.meta.client.delete_object(Bucket=self.bucket.name, Key=smart_template.file_key)
