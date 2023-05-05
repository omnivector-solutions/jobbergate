"""
Router dependencies job_script_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session, s3_bucket
from jobbergate_api.apps.job_script_templates.service import (
    JobScriptTemplateFilesService,
    JobScriptTemplateService,
)


async def template_service(session: AsyncSession = Depends(db_session)) -> JobScriptTemplateService:
    """
    Dependency to get the job_script_templates service.

    Returns:
        JobScriptTemplateService: The job_script_templates service.
    """
    return JobScriptTemplateService(session=session)


async def template_files_service(
    session: AsyncSession = Depends(db_session),
    bucket=Depends(s3_bucket),
) -> JobScriptTemplateFilesService:
    """Dependency to get the job_script_template_files service."""
    return JobScriptTemplateFilesService(session, bucket)
