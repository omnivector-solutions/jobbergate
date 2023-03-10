"""Services for the job_script_templates resource, including module specific business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest


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


def read():
    pass


def list():
    pass


def update():
    pass


def delete():
    pass
