"""
JobSubmission resource schema.
"""

from typing import Optional, Self
from datetime import datetime
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, field_validator

from jobbergate_api.apps.job_scripts.schemas import JobScriptBaseView, JobScriptDetailedView
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.schemas import LengthLimitedStr, TableResource
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_submission_meta_mapper = MetaMapper(
    id=MetaField(
        description="The unique database identifier for the instance",
        example=101,
    ),
    created_at=MetaField(
        description="The timestamp for when the instance was created",
        example="2023-08-18T13:55:37.172285",
    ),
    updated_at=MetaField(
        description="The timestamp for when the instance was last updated",
        example="2023-08-18T13:55:37.172285",
    ),
    name=MetaField(
        description="The unique name of the job submission",
        example="test-job-submission-77",
    ),
    description=MetaField(
        description="A text field providing a human-friendly description of the job_submission",
        example="Submission for the Foo job on sample 99 using the bar variant",
    ),
    owner_email=MetaField(
        description="The email of the owner/creator of the instance",
        example="tucker@omnivector.solutions",
    ),
    job_script_id=MetaField(
        description="The foreign-key to the job_script from which this instance was created",
        example=71,
    ),
    execution_directory=MetaField(
        description="The directory on the cluster where the job should be executed",
        example="/home/someuser/job-data/test-77",
    ),
    slurm_job_id=MetaField(
        description="The id for the slurm job executing this job_submission",
        example="1883",
    ),
    client_id=MetaField(
        description="The client_id of the cluster where this job submission should execute",
        example="mega-cluster-1",
    ),
    status=MetaField(
        description=f"The status of the job submission. Must be one of {JobSubmissionStatus.pretty_list()}",
        example=JobSubmissionStatus.CREATED,
    ),
    report_message=MetaField(
        description="The report message received from cluster-agent when a job submission is rejected",
        example="Unrecognized SBATCH arguments",
    ),
    slurm_job_state=MetaField(
        description="The Slurm Job state as reported by the agent.example",
        example="PENDING",
    ),
    slurm_job_info=MetaField(
        description="Detailed information about the Slurm Job as reported by the agent",
        example="""
            JobId=2 JobName=apptainer-test
            UserId=ubuntu(1000) GroupId=ubuntu(1000) MCS_label=N/A
            Priority=4294901758 Nice=0 Account=(null) QOS=normal
            JobState=RUNNING Reason=None Dependency=(null)
            Requeue=1 Restarts=0 BatchFlag=1 Reboot=0 ExitCode=0:0
            RunTime=00:01:57 TimeLimit=UNLIMITED TimeMin=N/A
            SubmitTime=2024-01-29T17:42:15 EligibleTime=2024-01-29T17:42:15
            AccrueTime=2024-01-29T17:42:15
            StartTime=2024-01-29T17:42:15 EndTime=Unknown Deadline=N/A
            SuspendTime=None SecsPreSuspend=0 LastSchedEval=2024-01-29T17:42:15 Scheduler=Main
            Partition=compute AllocNode:Sid=10.122.188.182:1278
            ReqNodeList=(null) ExcNodeList=(null)
            NodeList=democluster
            BatchHost=democluster
            NumNodes=1 NumCPUs=6 NumTasks=6 CPUs/Task=1 ReqB:S:C:T=0:0:*:*
            ReqTRES=cpu=6,mem=3903M,node=1,billing=6
            AllocTRES=cpu=6,node=1,billing=6
            Socks/Node=* NtasksPerN:B:S:C=0:0:*:* CoreSpec=*
            MinCPUsNode=1 MinMemoryNode=0 MinTmpDiskNode=0
            Features=(null) DelayBoot=00:00:00
            OverSubscribe=OK Contiguous=0 Licenses=(null) Network=(null)
            Command=(null)
            WorkDir=/tmp
            StdErr=/home/ubuntu/democluster/job.%J.err
            StdIn=/dev/null
            StdOut=/home/ubuntu/democluster/job.%J.out
            Power=
        """,
    ),
    is_archived=MetaField(
        description="Indicates if the job submission has been archived.",
        example=False,
    ),
    sbatch_arguments=MetaField(
        description="The arguments used to submit the job to the slurm queue",
        example=["--exclusive", "--job-name=example-job"],
    ),
    cloned_from_id=MetaField(
        description="Indicates the id this entry has been cloned from, if any.",
        example=101,
    ),
)


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    name: LengthLimitedStr
    description: Optional[LengthLimitedStr] = None
    job_script_id: NonNegativeInt
    slurm_job_id: Optional[NonNegativeInt] = None
    execution_directory: Optional[LengthLimitedStr] = None
    client_id: Optional[LengthLimitedStr] = None
    sbatch_arguments: Optional[list[LengthLimitedStr]] = Field(None, max_length=50)

    @field_validator("execution_directory", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Ensure empty strings are converted to None to avoid problems with Path downstream."""
        return v or None

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionUpdateRequest(BaseModel):
    """
    Request model for updating JobSubmission instances.
    """

    name: Optional[LengthLimitedStr] = None
    description: Optional[LengthLimitedStr] = None
    execution_directory: Optional[LengthLimitedStr] = None
    status: Optional[JobSubmissionStatus] = None

    @field_validator("execution_directory", mode="before")
    def empty_str_to_none(cls, v):
        """Ensure empty strings are converted to None to avoid problems with Path downstream."""
        return v or None

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionBaseView(TableResource):
    """
    Base model to match the database for the JobSubmission resource.

    Omits parent relationship.
    """

    job_script_id: Optional[int] = None
    slurm_job_id: Optional[int] = None
    client_id: str
    status: JobSubmissionStatus
    slurm_job_state: Optional[SlurmJobState] = None
    cloned_from_id: Optional[int] = None

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionListView(JobSubmissionBaseView):
    """
    Complete model to match the database for the JobSubmission resource in a list view.
    """

    job_script: Optional[JobScriptBaseView] = None


class JobSubmissionDetailedView(JobSubmissionBaseView):
    """
    Complete model to match the database for the JobSubmission resource in a detailed view.
    """

    execution_directory: Optional[str]
    report_message: Optional[str]
    slurm_job_info: Optional[str]
    sbatch_arguments: Optional[list[str]]


class PendingJobSubmission(BaseModel):
    """
    Specialized model for the cluster-agent to pull pending job_submissions.

    Model also includes data from its job_script and application sources.
    """

    id: int
    name: str
    owner_email: str
    execution_directory: Optional[str] = None
    execution_parameters: dict = Field(default_factory=dict)
    job_script: JobScriptDetailedView
    sbatch_arguments: Optional[list[str]] = None

    model_config = ConfigDict(
        from_attributes=True, extra="ignore", json_schema_extra=job_submission_meta_mapper
    )


class ActiveJobSubmission(BaseModel):
    """
    Specialized model for the cluster-agent to pull an active job_submission.
    """

    id: int
    name: str
    slurm_job_id: int
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class JobSubmissionAgentSubmittedRequest(BaseModel):
    """Request model for marking JobSubmission instances as SUBMITTED."""

    id: int
    slurm_job_id: NonNegativeInt
    slurm_job_state: SlurmJobState
    slurm_job_info: str
    slurm_job_state_reason: Optional[str] = None

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionAgentRejectedRequest(BaseModel):
    """Request model for marking JobSubmission instances as REJECTED."""

    id: int
    report_message: str

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionAgentUpdateRequest(BaseModel):
    """Request model for updating JobSubmission instances."""

    slurm_job_id: NonNegativeInt
    slurm_job_state: SlurmJobState
    slurm_job_info: str
    slurm_job_state_reason: Optional[str] = None

    model_config = ConfigDict(json_schema_extra=job_submission_meta_mapper)


class JobSubmissionAgentMaxTimes(BaseModel):
    """Model for the max_times field of the JobSubmissionMetricsMaxResponse."""

    max_time: int
    node_host: str
    step: int
    task: int

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class JobSubmissionAgentMetricsRequest(BaseModel):
    """Request model for updating JobSubmission instances."""

    job_submission_id: int
    max_times: list[JobSubmissionAgentMaxTimes]


class JobSubmissionMetricSchema(BaseModel):
    """Model for the JobSubmissionMetric resource.

    Both `step` and `task` are optional fields, as they are not relevant when the metrics are
    queried over all the nodes. As well as, all measurements are both `int` and `float` due to
    the aggregation done by the time series database over time. For better understanding on the
    math behind the aggregation, please refer to the alembic revision ``99c3877d0f10``.
    """

    time: int | datetime
    node_host: str
    step: Optional[int] = None
    task: Optional[int] = None
    cpu_frequency: int | float
    cpu_time: float
    cpu_utilization: float
    gpu_memory: int | float
    gpu_utilization: float
    page_faults: int | float
    memory_rss: int | float
    memory_virtual: int | float
    disk_read: int | float
    disk_write: int | float

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @field_validator("time", mode="before")
    @classmethod
    def validate_time(cls, v: int | datetime) -> int:
        """Ensure that the time is always an int."""
        if isinstance(v, datetime):
            return int(v.timestamp())
        return v

    @classmethod
    def from_iterable(cls, iterable: Iterable, skip_optional: bool = False) -> Self:
        """Convert an iterable containing the fields of the model to an instance of the model."""
        if skip_optional:
            fields = list(field_name for field_name, field in cls.model_fields.items() if field.is_required())
        else:
            fields = list(cls.model_fields.keys())

        if len(fields) != len(list(iterable)):
            raise ValueError("The iterable must have the same length as the model fields.")

        return cls(**{field: value for field, value in zip(fields, iterable)})


class JobSubmissionMetricTimestamps(BaseModel):
    """Model for the timestamps of the JobSubmissionMetric resource."""

    min: int
    max: int

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class JobProgressDetail(BaseModel):
    """
    Base model for the JobProgress resource.
    """

    id: int
    job_submission_id: int
    timestamp: datetime
    slurm_job_state: Optional[str] = None
    additional_info: Optional[str] = None
