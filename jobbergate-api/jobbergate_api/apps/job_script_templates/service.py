"""Services for the job_script_templates resource, including module specific business logic."""
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateUpdateRequest,
)


async def create_job_script_template(
    db: AsyncSession, incoming_data: JobTemplateCreateRequest, owner_email: str
) -> JobScriptTemplate:
    """Add a new job_script_template to the database."""
    job_script_template = JobScriptTemplate(
        **incoming_data.dict(exclude_unset=True),
        owner_email=owner_email,
    )
    db.add(job_script_template)
    await db.commit()
    await db.refresh(job_script_template)
    return job_script_template


async def read_job_script_template(db: AsyncSession, id_or_identifier: int | str) -> JobScriptTemplate | None:
    """Get a job_script_template by id or identifier."""
    query = select(JobScriptTemplate)
    query = _locate_by_id_or_identifier(id_or_identifier, query)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def count(db: AsyncSession) -> int:
    """Count the number of job_script_templates on the database."""
    result = await db.execute(select(sqlalchemy.func.count(JobScriptTemplate.id)))
    return result.scalar_one()


def list():
    pass


async def update(
    db: AsyncSession,
    id_or_identifier: int | str,
    incoming_data: JobTemplateUpdateRequest,
) -> JobScriptTemplate:
    """Update a job_script_template by id or identifier."""
    query = sqlalchemy.update(JobScriptTemplate).returning(JobScriptTemplate)
    query = _locate_by_id_or_identifier(id_or_identifier, query)
    query = query.values(**incoming_data.dict(exclude_unset=True))
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one()


async def delete_job_script_template(db: AsyncSession, id_or_identifier: int | str) -> None:
    """Delete a job_script_template by id or identifier."""
    job_template = await read_job_script_template(db, id_or_identifier)
    if job_template is None:
        return
    await db.delete(job_template)
    await db.commit()


def _locate_by_id_or_identifier(id_or_identifier: int | str, query):
    if isinstance(id_or_identifier, str):
        query = query.where(JobScriptTemplate.identifier == id_or_identifier)
    elif isinstance(id_or_identifier, int):
        query = query.where(JobScriptTemplate.id == id_or_identifier)
    else:
        raise ValueError("id_or_identifier must be a string or integer")
    return query
