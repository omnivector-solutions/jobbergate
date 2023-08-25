"""
Router dependencies shared for multiple resources.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Iterator

from aioboto3.session import Session
from fastapi import Depends

from jobbergate_api.apps.services import BucketBoundService, DatabaseBoundService
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


@contextmanager
def bind_session(session: AsyncSession) -> Iterator[None]:
    """Bind the session to all CRUD services."""
    try:
        [service.bind_session(session) for service in DatabaseBoundService.database_services]
        yield
    finally:
        [service.unbind_session() for service in DatabaseBoundService.database_services]


@contextmanager
def bind_bucket(bucket: Bucket) -> Iterator[None]:
    """Bind the bucket to all file services."""
    try:
        [service.bind_bucket(bucket) for service in BucketBoundService.bucket_services]
        yield
    finally:
        [service.unbind_bucket() for service in BucketBoundService.bucket_services]


@dataclass
class SecureService(SecureSession):
    """Dataclass to hold the secure session and the bucket."""

    bucket: Bucket


def secure_services(
    *scopes: str,
    permission_mode: PermissionMode = PermissionMode.ALL,
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
            with bind_session(secure_session.session), bind_bucket(bucket):
                yield SecureService(
                    identity_payload=secure_session.identity_payload,
                    session=secure_session.session,
                    bucket=bucket,
                )

    return dependency
