"""
Database model for the JobSubmission resource.
"""
from sqlalchemy import DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergate_api.metadata import metadata

job_submissions_table = Table(
    "job_submissions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("job_submission_name", String, nullable=False, index=True),
    Column("job_submission_description", String, default=""),
    Column("job_submission_owner_email", String, nullable=False, index=True),
    Column("job_script_id", ForeignKey("job_scripts.id"), nullable=False),
    Column("slurm_job_id", Integer, default=None),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),
)

searchable_fields = [
    job_submissions_table.c.job_submission_name,
    job_submissions_table.c.job_submission_description,
    job_submissions_table.c.job_submission_owner_email,
]
