"""
Database model for the JobScript resource.
"""
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import False_, func
from sqlalchemy.sql.schema import Column

from jobbergate_api.metadata import metadata

job_scripts_table = Table(
    "job_scripts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("job_script_name", String, nullable=False, index=True),
    Column("job_script_description", String, default=""),
    Column("job_script_owner_email", String, nullable=False, index=True),
    Column("application_id", ForeignKey("applications.id"), nullable=True),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),
    Column("is_archived", Boolean, nullable=False, default=False_()),
)

searchable_fields = [
    job_scripts_table.c.job_script_name,
    job_scripts_table.c.job_script_description,
    job_scripts_table.c.job_script_owner_email,
]

sortable_fields = [
    job_scripts_table.c.id,
    job_scripts_table.c.job_script_name,
    job_scripts_table.c.job_script_owner_email,
    job_scripts_table.c.application_id,
    job_scripts_table.c.created_at,
    job_scripts_table.c.updated_at,
]
