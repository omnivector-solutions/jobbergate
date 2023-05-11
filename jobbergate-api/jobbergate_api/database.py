"""Core module for database session related operations."""
from asyncio import current_task

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import sessionmaker

from jobbergate_api.storage import build_db_url

engine = create_async_engine(build_db_url(asynchronous=True), pool_pre_ping=True)
SessionLocal = async_scoped_session(
    sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    ),
    scopefunc=current_task,
)
