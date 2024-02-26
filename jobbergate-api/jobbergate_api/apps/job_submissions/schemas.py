"""
JobSubmission resource schema.
"""

from typing import Optional

from pydantic import BaseModel, Extra, Field, NonNegativeInt, validator

from jobbergate_api.apps.job_scripts.schemas import JobScriptDetailedView, JobScriptListView
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
        example="--ntasks=1 --cpus-per-task=1 --mem=4G --partition=compute",
    ),
)


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    name: LengthLimitedStr
    description: Optional[LengthLimitedStr]
    job_script_id: NonNegativeInt
    slurm_job_id: Optional[NonNegativeInt]
    execution_directory: Optional[LengthLimitedStr]
    client_id: Optional[LengthLimitedStr]
    sbatch_arguments: Optional[str] = Field(default=None, max_length=1024)

    @validator("execution_directory", pre=True, always=True)
    def empty_str_to_none(cls, v):
        """Ensure empty strings are converted to None to avoid problems with Path downstream."""
        return v or None

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionUpdateRequest(BaseModel):
    """
    Request model for updating JobSubmission instances.
    """

    name: Optional[LengthLimitedStr]
    description: Optional[LengthLimitedStr]
    execution_directory: Optional[LengthLimitedStr]
    status: Optional[JobSubmissionStatus]

    @validator("execution_directory", pre=True, always=True)
    def empty_str_to_none(cls, v):
        """Ensure empty strings are converted to None to avoid problems with Path downstream."""
        return v or None

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionListView(TableResource):
    """
    Partial model to match the database for the JobSubmission resource.
    """

    job_script_id: Optional[int]
    slurm_job_id: Optional[int]
    client_id: str
    status: JobSubmissionStatus
    slurm_job_state: Optional[SlurmJobState]

    job_script: Optional[JobScriptListView]

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionDetailedView(JobSubmissionListView):
    """
    Complete model to match the database for the JobSubmission resource.
    """

    execution_directory: Optional[str]
    report_message: Optional[str]
    slurm_job_info: Optional[str]
    sbatch_arguments: Optional[str]


class PendingJobSubmission(BaseModel):
    """
    Specialized model for the cluster-agent to pull pending job_submissions.

    Model also includes data from its job_script and application sources.
    """

    id: int
    name: str
    owner_email: str
    execution_directory: Optional[str]
    execution_parameters: dict = Field(default_factory=dict)
    job_script: JobScriptDetailedView
    sbatch_arguments: Optional[str]

    class Config:
        orm_mode = True
        extra = Extra.ignore
        schema_extra = job_submission_meta_mapper


class ActiveJobSubmission(BaseModel):
    """
    Specialized model for the cluster-agent to pull an active job_submission.
    """

    id: int
    name: str
    slurm_job_id: int

    class Config:
        orm_mode = True
        extra = Extra.ignore


class JobSubmissionAgentSubmittedRequest(BaseModel):
    """Request model for marking JobSubmission instances as SUBMITTED."""

    id: int
    slurm_job_id: Optional[NonNegativeInt]

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionAgentRejectedRequest(BaseModel):
    """Request model for marking JobSubmission instances as REJECTED."""

    id: int
    report_message: str

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionAgentUpdateRequest(BaseModel):
    """Request model for updating JobSubmission instances."""

    slurm_job_id: NonNegativeInt
    slurm_job_state: SlurmJobState
    slurm_job_info: str
    slurm_job_state_reason: Optional[str]

    class Config:
        schema_extra = job_submission_meta_mapper
