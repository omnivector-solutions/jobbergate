"""
Database model for the JobScript resource.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergateapi2.metadata import metadata

job_scripts_table = Table(
    "job_scripts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("job_script_name", String, nullable=False, index=True),
    Column("job_script_description", String, default=""),
    Column("job_script_data_as_string", String, nullable=False),
    Column("job_script_owner_id", String, nullable=False, index=True),
    Column("application_id", ForeignKey("applications.id")),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=datetime.utcnow),
)
