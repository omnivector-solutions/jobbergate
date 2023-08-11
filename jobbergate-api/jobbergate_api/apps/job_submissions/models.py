"""
Database model for the JobSubmission resource.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_scripts.models import JobScript as JobScriptModel
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.models import Base, CrudMixin
from jobbergate_api.safe_types import JobScript


class JobSubmission(CrudMixin, Base):
    """
    Job submission table definition.

    Notice all relationships are lazy="raise" to prevent n+1 implicit queries.
    This means that the relationships must be explicitly eager loaded using
    helper functions in the class.

    Attributes:
        job_script_id: Id number of the job scrip this submissions is based on.
        execution_directory: The directory where the job is executed.
        slurm_job_id: The id of the job in the slurm queue.
        client_id: The id of the custer this submission runs on.
        status: The status of the job submission.
        report_message: The message returned by the job.
        execution_parameters: The properties of the job.

    See Mixin class definitions for other columns
    """

    job_script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_scripts.id", ondelete="SET NULL"), nullable=True
    )
    execution_directory: Mapped[str] = mapped_column(String, default=None, nullable=True)
    slurm_job_id: Mapped[int] = mapped_column(Integer, default=None, nullable=True)
    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[JobSubmissionStatus] = mapped_column(
        Enum(JobSubmissionStatus, native_enum=False), nullable=False, index=True
    )
    report_message: Mapped[str] = mapped_column(String, nullable=True)
    execution_parameters: Mapped[dict[str, Any]] = mapped_column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    job_script: Mapped[JobScript] = relationship(
        "JobScript",
        back_populates="submissions",
        lazy="raise",
    )

    @classmethod
    def searchable_fields(cls):
        """
        Add client_id as a searchable field.
        """
        return {cls.client_id, *super().searchable_fields()}

    @classmethod
    def sortable_fields(cls):
        """
        Add additional sortable fields.
        """
        return {
            cls.job_script_id,
            cls.slurm_job_id,
            cls.client_id,
            cls.status,
            *super().sortable_fields(),
        }

    @classmethod
    def include_files(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load files.
        """
        return query.options(selectinload(cls.job_script).options(selectinload(JobScriptModel.files)))

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load parent data.
        """
        return query.options(selectinload(cls.job_script).load_only(JobScriptModel.id, JobScriptModel.name))
