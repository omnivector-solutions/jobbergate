"""
Router dependencies shared for multiple resources.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""

from aioboto3.session import Session

from jobbergate_api.config import settings
from jobbergate_api.database import SessionLocal


async def db_session():
    """
    Dependency to get the database session.

    Yields:
        AsyncSession: The database session.
    """
    async with SessionLocal() as session:
        async with session.begin():
            yield session


async def s3_bucket():
    """
    Dependency to get the S3 bucket object.

    Note:
        See https://aioboto3.readthedocs.io/en/latest/usage.html for more information
        on how to use aioboto3.
    """
    session = Session()
    async with session.resource("s3", endpoint_url=settings.S3_ENDPOINT_URL) as s3:
        bucket = await s3.Bucket(settings.S3_BUCKET_NAME)
        yield bucket
