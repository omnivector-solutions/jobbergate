"""Services for the job_script_templates resource, including module specific business logic."""
import dataclasses
import io
from typing import Any

from fastapi import UploadFile
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.job_scripts.schemas import JobScriptCreateRequest, JobScriptUpdateRequest
from jobbergate_api.storage import search_clause, sort_clause


@dataclasses.dataclass
class JobScriptService:
    session: AsyncSession

    async def create(
        self,
        incoming_data: JobScriptCreateRequest,
        owner_email: str,
        parent_template_id: int | None = None,
    ) -> JobScript:
        """Add a new job script to the database."""

        job_script = JobScript(
            **incoming_data.dict(exclude_unset=True),
            parent_template_id=parent_template_id,
            owner_email=owner_email,
        )
        self.session.add(job_script)
        await self.session.flush()
        await self.session.refresh(job_script)
        return job_script

    async def count(self) -> int:
        """Count the number of job_script on the database."""
        result = await self.session.execute(select(func.count(JobScript.id)))
        return result.scalar_one()

    async def get(self, id: int) -> JobScript | None:
        """Get a job script by id."""
        query = select(JobScript)
        query = query.where(JobScript.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> None:
        """Delete a job script by id."""
        job_script = await self.get(id)
        if job_script is None:
            raise NoResultFound("JobScript not found")
        await self.session.delete(job_script)
        await self.session.flush()

    async def update(self, id: int, incoming_data: JobScriptUpdateRequest) -> JobScript:
        """Update a job script by id."""
        query = update(JobScript).returning(JobScript)
        query = query.where(JobScript.id == id)
        query = query.values(**incoming_data.dict(exclude_unset=True))
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one()

    async def list(
        self,
        user_email: str | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        sort_ascending: bool = True,
        from_job_script_template_id: int | None = None,
    ) -> Page[JobScript]:
        """List job scripts."""
        query = select(JobScript)
        if user_email:
            query = query.where(JobScript.owner_email == user_email)
        if from_job_script_template_id is not None:
            query = query.where(JobScript.parent_template_id == from_job_script_template_id)
        if search:
            query = query.where(search_clause(search, JobScript.searchable_fields))
        if sort_field:
            query = query.order_by(sort_clause(sort_field, JobScript.sortable_fields, sort_ascending))
        return await paginate(self.session, query)


@dataclasses.dataclass
class JobScriptFilesService:
    session: AsyncSession
    bucket: Any

    async def get(self, job_script_file: JobScriptFile):
        """Get a job_script_template file."""
        file_content = await self._get_file_content(job_script_file)
        yield file_content

    async def _get_file_content(self, template_file: JobScriptFile):
        fileobj = await self.bucket.meta.client.get_object(
            Bucket=self.bucket.name, Key=template_file.file_key
        )
        return await fileobj["Body"].read()

    async def upsert(
        self,
        job_script_id: int,
        file_type: FileType,
        upload_content: str | bytes | UploadFile,
        filename: str,
    ) -> JobScriptFile:
        """Upsert a job_script file."""
        template_file = JobScriptFile(id=job_script_id, filename=filename, file_type=file_type)

        if isinstance(upload_content, str):
            file_obj: Any = io.BytesIO(upload_content.encode())
        elif isinstance(upload_content, bytes):
            file_obj = io.BytesIO(upload_content)
        elif isinstance(upload_content, UploadFile):
            file_obj = upload_content.file
        else:
            raise TypeError(f"Unsupported file type {type(upload_content)}")

        await self.bucket.upload_fileobj(Fileobj=file_obj, Key=template_file.file_key)

        merged = await self.session.merge(template_file)
        await self.session.flush()
        return merged

    async def delete(self, template_file: JobScriptFile) -> None:
        """Delete a job_script_template file."""
        await self.session.delete(template_file)
        await self.bucket.meta.client.delete_object(Bucket=self.bucket.name, Key=template_file.file_key)
        await self.session.flush()
