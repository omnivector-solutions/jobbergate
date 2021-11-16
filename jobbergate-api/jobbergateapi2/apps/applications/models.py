"""
Database model for the Application resource.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Table
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergateapi2.metadata import metadata

applications_table = Table(
    "applications",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("application_name", String, nullable=False, index=True),
    Column("application_description", String, default=""),
    Column("application_owner_id", String, nullable=False, index=True),
    Column("application_file", String, nullable=False),
    Column("application_config", String, nullable=False),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=datetime.utcnow),
)
