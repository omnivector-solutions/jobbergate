"""
Router dependencies job_script_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session
from jobbergate_api.apps.job_script_templates.service import JobScriptTemplateService


async def template_service(session: AsyncSession = Depends(db_session)) -> JobScriptTemplateService:
    """
    Dependency to get the job_script_templates service.

    Returns:
        JobScriptTemplateService: The job_script_templates service.
    """
    return JobScriptTemplateService(session=session)
