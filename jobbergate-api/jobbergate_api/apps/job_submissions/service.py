"""Services for the job_submission_templates resource, including module specific business logic."""
import dataclasses

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.job_submissions.schemas import JobSubmissionCreateRequest, JobSubmissionUpdateRequest
from jobbergate_api.storage import search_clause, sort_clause


@dataclasses.dataclass
class JobSubmissionService:
    session: AsyncSession

    async def create(
        self,
        incoming_data: JobSubmissionCreateRequest,
        owner_email: str,
    ) -> JobSubmission:
        """Add a new job submission to the database."""

        job_submission = JobSubmission(
            **incoming_data.dict(exclude_unset=True),
            owner_email=owner_email,
            status=JobSubmissionStatus.CREATED,
        )
        self.session.add(job_submission)
        await self.session.flush()
        await self.session.refresh(job_submission)
        return job_submission

    async def count(self) -> int:
        """Count the number of job_submission on the database."""
        result = await self.session.execute(select(func.count(JobSubmission.id)))
        return result.scalar_one()

    async def get(self, id: int, join: bool = False) -> JobSubmission | None:
        """Get a job submission by id."""
        query = select(JobSubmission)
        if join:
            query = query.join(JobScript)
        query = query.where(JobSubmission.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> None:
        """Delete a job submission by id."""
        job_submission = await self.get(id)
        if job_submission is None:
            raise NoResultFound("JobSubmission not found")
        await self.session.delete(job_submission)
        await self.session.flush()

    async def update(self, id: int, incoming_data: JobSubmissionUpdateRequest) -> JobSubmission:
        """Update a job submission by id."""
        query = update(JobSubmission).returning(JobSubmission)
        query = query.where(JobSubmission.id == id)
        query = query.values(**incoming_data.dict(exclude_unset=True))
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one()

    async def list(
        self,
        user_email: str | None = None,
        slurm_job_ids: list[int] | None = None,
        submit_status: JobSubmissionStatus | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        sort_ascending: bool = True,
        from_job_script_id: int | None = None,
    ) -> Page[JobSubmission]:
        """List job submissions."""
        query = select(JobSubmission)
        if user_email:
            query = query.where(JobSubmission.owner_email == user_email)
        if slurm_job_ids:
            query = query.where(JobSubmission.slurm_job_id.in_(slurm_job_ids))
        if submit_status:
            query = query.where(JobSubmission.status == submit_status)
        if from_job_script_id is not None:
            query = query.where(JobSubmission.job_script_id == from_job_script_id)
        if search:
            query = query.where(search_clause(search, JobSubmission.searchable_fields))
        if sort_field:
            query = query.order_by(sort_clause(sort_field, JobSubmission.sortable_fields, sort_ascending))
        return await paginate(self.session, query)
