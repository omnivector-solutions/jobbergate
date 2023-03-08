"""
Database model for the JobSubmission resource.
"""
from typing import Any
from sqlalchemy import Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.schema import Column

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.models import Base, BaseFieldsMixin, ExtraFieldsMixin


class JobSubmission(Base, BaseFieldsMixin, ExtraFieldsMixin):
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

    id: int = Column(Integer, primary_key=True)
    job_script_id: int = Column(Integer, ForeignKey("job_scripts.id"), nullable=False)
    execution_directory: str = Column(String)
    slurm_job_id: int = Column(Integer, default=None)
    client_id: str = Column(String, nullable=False, index=True)
    status: JobSubmissionStatus = Column(Enum(JobSubmissionStatus), nullable=False, index=True)
    report_message: str = Column(String, nullable=True)
    execution_parameters: dict[str, Any] = Column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )


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
