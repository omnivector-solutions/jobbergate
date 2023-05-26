"""
Database model for the JobSubmission resource.
"""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import functions

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.models import Base, Mapped, mapped_column


class JobSubmission(Base):
    """
    Job submission table definition.

    Attributes:
        id: The id of the job submission.
        name: The name of the job submission.
        description: The description of the job submission.
        owner_email: The email of the owner of the job submission.
        job_script_id: Id number of the job scrip this submissions is based on.
        execution_directory: The directory where the job is executed.
        slurm_job_id: The id of the job in the slurm queue.
        client_id: The id of the custer this submission runs on.
        status: The status of the job submission.
        report_message: The message returned by the job.
        execution_parameters: The properties of the job.
        created_at: The date and time when the job submission was created.
        updated_at: The date and time when the job submission was updated.
    """

    __tablename__ = "job_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_script_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_scripts.id"), nullable=False)
    execution_directory: Mapped[str] = mapped_column(String)
    slurm_job_id: Mapped[int] = mapped_column(Integer, default=None)
    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[JobSubmissionStatus] = mapped_column(Enum(JobSubmissionStatus), nullable=False, index=True)
    report_message: Mapped[str] = mapped_column(String, nullable=True)
    execution_parameters: Mapped[dict[str, Any]] = mapped_column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, default=None, nullable=True)
    owner_email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=functions.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=functions.now(),
        onupdate=functions.current_timestamp(),
    )

    searchable_fields = [
        name,
        description,
        owner_email,
        client_id,
    ]

    sortable_fields = [
        id,
        name,
        owner_email,
        job_script_id,
        slurm_job_id,
        client_id,
        created_at,
        updated_at,
        status,
    ]


job_submissions_table = JobSubmission.__table__

searchable_fields = [
    job_submissions_table.c.name,
    job_submissions_table.c.description,
    job_submissions_table.c.owner_email,
    job_submissions_table.c.client_id,
]

sortable_fields = [
    job_submissions_table.c.id,
    job_submissions_table.c.name,
    job_submissions_table.c.owner_email,
    job_submissions_table.c.job_script_id,
    job_submissions_table.c.slurm_job_id,
    job_submissions_table.c.client_id,
    job_submissions_table.c.created_at,
    job_submissions_table.c.updated_at,
    job_submissions_table.c.status,
]
