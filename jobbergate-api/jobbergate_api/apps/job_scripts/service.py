"""Services for the job_script_templates resource, including module specific business logic."""
import dataclasses
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.job_scripts.schemas import JobScriptCreateRequest, JobScriptUpdateRequest


@dataclasses.dataclass
class JobScriptService:

    session: AsyncSession

    async def create(self, incoming_data: JobScriptCreateRequest, owner_email: str) -> JobScript:
        """Add a new job_script_template to the database."""

        job_script = JobScript(
            **incoming_data.dict(exclude_unset=True),
            owner_email=owner_email,
        )
        self.session.add(job_script)
        await self.session.flush()
        await self.session.refresh(job_script)
        return job_script

    async def count(self) -> int:
        """Count the number of job_script_templates on the database."""
        result = await self.session.execute(select(func.count(JobScript.id)))
        return result.scalar_one()

    async def get(self, id: int) -> JobScript | None:
        """Get a job_script_template by id or identifier."""
        query = select(JobScript)
        query = query.where(JobScript.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> None:
        """Delete a job_script_template by id or identifier."""
        job_template = await self.get(id)
        if job_template is None:
            raise NoResultFound("JobScript not found")
        await self.session.delete(job_template)
        await self.session.flush()

    async def update(self, id: int, incoming_data: JobScriptUpdateRequest) -> JobScript:
        """Update a job_script_template by id or identifier."""
        query = update(JobScript).returning(JobScript)
        query = query.where(JobScript.id == id)
        query = query.values(**incoming_data.dict(exclude_unset=True))
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one()


def list():
    pass


@dataclasses.dataclass
class JobScriptFilesService:

    session: AsyncSession
    bucket: Any

    async def get(self, job_script_file: JobScriptFile):
        """Get a job_script_template file."""
        fileobj = await self.bucket.meta.client.get_object(
            Bucket=self.bucket.name, Key=job_script_file.file_key
        )
        yield fileobj

    async def upsert(
        self,
        job_script_id: int,
        file_type: FileType,
        upload_file: UploadFile,
    ) -> JobScriptFile:
        """Upsert a job_script file."""
        template_file = JobScriptFile(id=job_script_id, filename=upload_file.filename, file_type=file_type)

        await self.bucket.upload_fileobj(Fileobj=upload_file.file, Key=template_file.file_key)

        await self.session.merge(template_file)
        await self.session.flush()
        await self.session.refresh(template_file)
        return template_file

    async def delete(self, template_file: JobScriptFile) -> None:
        """Delete a job_script_template file."""
        await self.session.delete(template_file)
        await self.bucket.meta.client.delete_object(Bucket=self.bucket.name, Key=template_file.file_key)
        await self.session.flush()
