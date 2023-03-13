"""
Router dependencies shared for multiple resources.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""

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
