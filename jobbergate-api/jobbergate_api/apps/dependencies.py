"""
Router dependencies shared for multiple resources.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""

from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from itertools import chain
from typing import AsyncIterator, Iterator, NamedTuple

from aioboto3.session import Session
from fastapi import Depends

from jobbergate_api.apps.job_script_templates.models import (
    JobScriptTemplate,
    JobScriptTemplateFile,
    WorkflowFile,
)
from jobbergate_api.apps.job_script_templates.services import (
    JobScriptTemplateFileService,
    JobScriptTemplateService,
)
from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.job_scripts.services import JobScriptCrudService, JobScriptFileService
from jobbergate_api.apps.job_submissions.models import JobSubmission, JobProgress
from jobbergate_api.apps.job_submissions.services import JobSubmissionService, JobProgressService
from jobbergate_api.config import settings
from jobbergate_api.safe_types import Bucket
from jobbergate_api.security import PermissionMode
from jobbergate_api.storage import AsyncSession, SecureSession, secure_session

session = Session()


@asynccontextmanager
async def s3_bucket(bucket_name: str, s3_url: str | None) -> AsyncIterator[Bucket]:
    """Create a bucket using a context manager."""
    async with session.resource("s3", endpoint_url=s3_url) as s3:
        bucket = await s3.Bucket(bucket_name)
        yield bucket


def get_bucket_name(override_bucket_name: str | None = None) -> str:
    """
    Get the bucket name based on the environment.

    The name can be overridden when multi tenancy is enabled by passing a bucket name.
    """
    if settings.DEPLOY_ENV.lower() == "test":
        return settings.TEST_S3_BUCKET_NAME
    if override_bucket_name and settings.MULTI_TENANCY_ENABLED:
        return override_bucket_name
    return settings.S3_BUCKET_NAME


def get_bucket_url() -> str | None:
    """Get the bucket url based on the environment."""
    if settings.DEPLOY_ENV.lower() == "test":
        return settings.TEST_S3_ENDPOINT_URL
    return settings.S3_ENDPOINT_URL


class CrudServices(NamedTuple):
    """Provide a container class for the CRUD services."""

    template: JobScriptTemplateService
    job_script: JobScriptCrudService
    job_submission: JobSubmissionService
    job_progress: JobProgressService


class FileServices(NamedTuple):
    """Provide a container class for the file services."""

    template: JobScriptTemplateFileService
    workflow: JobScriptTemplateFileService
    job_script: JobScriptFileService


class Services(NamedTuple):
    """Provide a container class for the services."""

    crud: CrudServices
    file: FileServices


@dataclass
class SecureService(SecureSession):
    """Dataclass to hold the secure session and the bucket."""

    bucket: Bucket
    crud: CrudServices
    file: FileServices


@contextmanager
def service_factory(session: AsyncSession, bucket: Bucket) -> Iterator[Services]:
    """Create the services and bind them to a db section and s3 bucket."""
    crud = CrudServices(
        template=JobScriptTemplateService(model_type=JobScriptTemplate),
        job_script=JobScriptCrudService(model_type=JobScript),
        job_submission=JobSubmissionService(model_type=JobSubmission),
        job_progress=JobProgressService(model_type=JobProgress),
    )
    file = FileServices(
        template=JobScriptTemplateFileService(model_type=JobScriptTemplateFile),
        workflow=JobScriptTemplateFileService(model_type=WorkflowFile),
        job_script=JobScriptFileService(model_type=JobScriptFile),
    )

    [service.bind_session(session) for service in chain(crud, file)]
    [service.bind_bucket(bucket) for service in file]

    yield Services(crud=crud, file=file)

    [service.unbind_session() for service in chain(crud, file)]
    [service.unbind_bucket() for service in file]


def secure_services(
    *scopes: str,
    permission_mode: PermissionMode = PermissionMode.SOME,
    commit: bool = True,
    ensure_email: bool = False,
    ensure_client_id: bool = False,
):
    """
    Dependency to bind database services to a secure session.
    """

    async def dependency(
        secure_session: SecureSession = Depends(
            secure_session(
                *scopes,
                permission_mode=permission_mode,
                commit=commit,
                ensure_email=ensure_email,
                ensure_organization=settings.MULTI_TENANCY_ENABLED is True,
                ensure_client_id=ensure_client_id,
            )
        ),
    ) -> AsyncIterator[SecureService]:
        """
        Bind each service to the secure session and then return the session.
        """
        bucket_name = get_bucket_name(secure_session.identity_payload.organization_id)
        s3_url = get_bucket_url()

        async with s3_bucket(bucket_name, s3_url) as bucket:
            with service_factory(secure_session.session, bucket) as services:
                yield SecureService(
                    identity_payload=secure_session.identity_payload,
                    session=secure_session.session,
                    bucket=bucket,
                    crud=services.crud,
                    file=services.file,
                )

    return dependency
