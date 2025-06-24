"""
Database model for the JobSubmission resource.
"""

from __future__ import annotations
from datetime import datetime, timezone

from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import (
    ARRAY,
    Dialect,
    Enum,
    ForeignKey,
    Integer,
    String,
    Float,
    Index,
    PrimaryKeyConstraint,
    BigInteger,
    DateTime as DateTimeColumn,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.expression import Select
from sqlalchemy.types import DateTime, TypeDecorator

from jobbergate_api.apps.job_scripts.models import JobScript as JobScriptModel
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.models import Base, CrudMixin, CommonMixin
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
        slurm_job_state: The Slurm Job state as reported by the agent
        slurm_job_info: Detailed information about the  Slurm Job as reported by the agent
        client_id: The id of the cluster this submission runs on.
        status: The status of the job submission.
        report_message: The message returned by the job.
        sbatch_arguments: The arguments used to submit the job to the slurm queue.

    See Mixin class definitions for other columns
    """

    job_script_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_scripts.id", ondelete="SET NULL"),
        nullable=True,
    )
    execution_directory: Mapped[str] = mapped_column(String, default=None, nullable=True)

    slurm_job_id: Mapped[int] = mapped_column(Integer, default=None, nullable=True)
    slurm_job_state: Mapped[SlurmJobState] = mapped_column(
        Enum(SlurmJobState, native_enum=False),
        nullable=True,
    )
    slurm_job_info: Mapped[str] = mapped_column(String, default=None, nullable=True)

    client_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[JobSubmissionStatus] = mapped_column(
        Enum(JobSubmissionStatus, native_enum=False),
        nullable=False,
        index=True,
    )
    report_message: Mapped[str] = mapped_column(String, nullable=True)
    sbatch_arguments: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    job_script: Mapped[JobScript] = relationship(
        "JobScript",
        back_populates="submissions",
        lazy="raise",
    )
    metrics: Mapped[list["JobSubmissionMetric"]] = relationship(
        "JobSubmissionMetric",
        back_populates="job_submission",
        lazy="raise",
    )
    progress_entries: Mapped[list["JobProgress"]] = relationship(
        "JobProgress",
        back_populates="job_submission",
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
            cls.slurm_job_state,
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
        return query.options(selectinload(cls.job_script))

    @classmethod
    def include_metrics(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load metrics.
        """
        return query.options(selectinload(cls.metrics))

    @classmethod
    def include_progress(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load progress entries.
        """
        return query.options(selectinload(cls.progress_entries))


class TimestampInt(TypeDecorator):
    impl = DateTime(timezone=True)

    def process_bind_param(self, value: int | None, dialect: Dialect) -> datetime | None:
        if value is not None:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> int | None:
        if value is not None:
            return int(value.timestamp())
        return value


class JobSubmissionMetric(CommonMixin, Base):
    """
    Job submission metric table definition.

    Attributes:
        time: The time the metric was recorded.
        job_submission_id: The id of the job submission this metric is for.
        slurm_job_id: The id of the job in the slurm queue.
        node_host: The node on which the metric was recorded.
        step: The step for which the metric was recorded.
        task: The task for which the metric was recorded.
        cpu_frequency: The CPU frequency at the time.
        cpu_time: The CPU time (system + user) consumed at the time.
        cpu_utilization: The CPU utilization (% of available) consumed at the time.
        gpu_memory: The GPU memory consumed at the time (in MB).
        gpu_utilization: The GPU utilizaiton (% of availavble) consumed at the time.
        page_faults: The number of page faults at the time.
        memory_rss: The resident set size of memory consumed at the time (in MB).
        memory_virtual: The virtual memory allocated at the time (in MB).
        disc_read: The amount of data read from disk at the time (in MB).
        disk_write: The amount of data written to disk at the time (in MB).
    """

    time: Mapped[int] = mapped_column(TimestampInt, nullable=False, index=True)
    job_submission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    slurm_job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    node_host: Mapped[str] = mapped_column(String, nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    task: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cpu_frequency: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_time: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    gpu_memory: Mapped[int] = mapped_column(BigInteger, nullable=False)
    gpu_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    page_faults: Mapped[int] = mapped_column(BigInteger, nullable=False)
    memory_rss: Mapped[int] = mapped_column(BigInteger, nullable=False)
    memory_virtual: Mapped[int] = mapped_column(BigInteger, nullable=False)
    disk_read: Mapped[int] = mapped_column(BigInteger, nullable=False)
    disk_write: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("time", "job_submission_id", "node_host", "step", "task"),
        Index("idx_node_host_step_task", "node_host", "step", "task"),
    )

    job_submission: Mapped[JobSubmission] = relationship(
        "JobSubmission",
        back_populates="metrics",
        lazy="raise",
    )

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load parent data.
        """
        return query.options(selectinload(cls.job_submission))


class JobProgress(CommonMixin, Base):
    """
    Job progress table definition.

    Attributes:
        id: Primary key
        job_submission_id: Foreign key to the job submission
        timestamp: When the progress entry was recorded
        slurm_job_state: The state of the Slurm job at this point
        additional_info: Any additional information about the job state
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_submission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[PendulumDateTime] = mapped_column(
        DateTimeColumn(timezone=True), nullable=False, default=PendulumDateTime.utcnow
    )
    slurm_job_state: Mapped[str] = mapped_column(String, nullable=True)
    additional_info: Mapped[str] = mapped_column(String, nullable=True)

    job_submission: Mapped[JobSubmission] = relationship(
        "JobSubmission",
        back_populates="progress_entries",
        lazy="raise",
    )

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load parent data.
        """
        return query.options(selectinload(cls.job_submission))

    @classmethod
    def sortable_fields(cls):
        """
        Add additional sortable fields.
        """
        return {
            cls.id,
            cls.job_submission_id,
            cls.timestamp,
            cls.slurm_job_state,
        }
