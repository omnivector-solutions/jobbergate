"""
Router dependencies job_script_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session, s3_bucket
from jobbergate_api.apps.job_script_templates.models import (
    JobScriptTemplate,
    JobScriptTemplateFile,
    WorkflowFile,
)
from jobbergate_api.apps.services import FileService, TableService


def template_service(session: AsyncSession = Depends(db_session)) -> TableService:
    """Dependency to get the job_script_templates service."""
    return TableService(db_session=session, base_table=JobScriptTemplate)


def template_files_service(
    session: AsyncSession = Depends(db_session),
    bucket=Depends(s3_bucket),
) -> FileService:
    """Dependency to get the job_script_template_files service."""
    return FileService(db_session=session, bucket=bucket, base_table=JobScriptTemplateFile)


def workflow_files_service(
    session: AsyncSession = Depends(db_session),
    bucket=Depends(s3_bucket),
) -> FileService:
    """Dependency to get the job_script_template_files service."""
    return FileService(db_session=session, bucket=bucket, base_table=WorkflowFile)
