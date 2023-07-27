"""
Router dependencies shared for multiple resources.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from typing import AsyncIterator

from aioboto3.session import Session
from fastapi import Depends

from jobbergate_api.apps.services import BucketBoundService, DatabaseBoundService
from jobbergate_api.config import settings
from jobbergate_api.safe_types import Bucket
from jobbergate_api.security import PermissionMode
from jobbergate_api.storage import SecureSession, secure_session


async def s3_bucket():
    """
    Dependency to get the S3 bucket object.

    Note:
        See https://aioboto3.readthedocs.io/en/latest/usage.html for more information
        on how to use aioboto3.
    """
    session = Session()
    if settings.DEPLOY_ENV.lower() == "test":
        s3_url = settings.TEST_S3_ENDPOINT_URL
        bucket_name = settings.TEST_S3_BUCKET_NAME
    else:
        s3_url = settings.S3_ENDPOINT_URL
        bucket_name = settings.S3_BUCKET_NAME
    async with session.resource("s3", endpoint_url=s3_url) as s3:
        bucket = await s3.Bucket(bucket_name)
        yield bucket


def file_services(*services: BucketBoundService):
    """
    Dependency to bind file services to a bucket.
    """

    async def dependency(
        bucket: Bucket = Depends(s3_bucket),
    ) -> AsyncIterator[SecureSession]:
        """
        Bind each service to the secure session and then return the session.
        """
        try:
            [service.bind_bucket(bucket) for service in services]
            yield bucket
        finally:
            [service.unbind_bucket() for service in services]

    return dependency


def secure_services(
    *scopes: str,
    permission_mode: PermissionMode = PermissionMode.ALL,
    services: list[DatabaseBoundService] | None = None,
):
    """
    Dependency to bind database services to a secure session.
    """
    if services is None:
        services = []

    async def dependency(
        secure_session: SecureSession = Depends(secure_session(*scopes, permission_mode=permission_mode)),
    ) -> AsyncIterator[SecureSession]:
        """
        Bind each service to the secure session and then return the session.
        """
        # Make type checkers happy
        assert services is not None

        try:
            [service.bind_session(secure_session.session) for service in services]
            yield secure_session
        finally:
            [service.unbind_session() for service in services]

    return dependency
