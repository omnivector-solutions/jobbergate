"""
JobSubmission resource schema.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Extra, Field

from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_submission_meta_mapper = MetaMapper(
    id=MetaField(
        description="The unique database identifier for the instance",
        example=101,
    ),
    created_at=MetaField(
        description="The timestamp for when the instance was created",
        example="2021-12-28 23:13:00",
    ),
    updated_at=MetaField(
        description="The timestamp for when the instance was last updated",
        example="2021-12-28 23:52:00",
    ),
    job_submission_name=MetaField(
        description="The unique name of the job submission",
        example="test-job-submission-77",
    ),
    job_submission_description=MetaField(
        description="A text field providing a human-friendly description of the job_submission",
        example="Submission for the Foo job on sample 99 using the bar variant",
    ),
    job_submission_owner_email=MetaField(
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
    execution_parameters=MetaField(
        description=(
            "The parameters to be passed to the job submission. "
            "See more details at: https://slurm.schedmd.com/rest_api.html"
        ),
        example={"name": "job-submission-name", "comment": "I am a comment"},
    ),
)


class JobProperties(BaseModel, extra=Extra.forbid):
    """
    Specialized model for job properties.

    See more details at: https://slurm.schedmd.com/rest_api.html
    """

    account: Optional[str] = Field(
        description="Charge resources used by this job to specified account.",
    )
    account_gather_frequency: Optional[str] = Field(
        description="Define the job accounting and profiling sampling intervals.",
    )
    argv: Optional[List[str]] = Field(description="Arguments to the script.")
    array: Optional[str] = Field(
        description=(
            "Submit a job array, multiple jobs to be executed with identical parameters. "
            "The indexes specification identifies what array index values should be used."
        )
    )
    batch_features: Optional[str] = Field(description="features required for batch script's node")
    begin_time: Optional[str] = Field(
        description=(
            "Submit the batch script to the Slurm controller immediately, like normal, "
            "but tell the controller to defer the allocation of the job until the specified time."
        )
    )
    burst_buffer: Optional[str] = Field(description="Burst buffer specification.")
    cluster_constraints: Optional[str] = Field(
        description=(
            "Specifies features that a federated cluster must have to have a sibling job submitted to it."
        )
    )
    comment: Optional[str] = Field(description="An arbitrary comment.")
    constraints: Optional[str] = Field(description="node features required by job.")
    core_specification: Optional[int] = Field(
        description=(
            "Count of specialized threads per node reserved by the job for system "
            "operations and not used by the application."
        )
    )
    cores_per_socket: Optional[int] = Field(
        description=(
            "Restrict node selection to nodes with at least the specified number of cores per socket."
        )
    )
    cpu_binding: Optional[str] = Field(description="Cpu binding")
    cpu_binding_hint: Optional[str] = Field(description="Cpu binding hint")
    cpu_frequency: Optional[str] = Field(
        description=(
            "Request that job steps initiated by srun commands inside this sbatch "
            "script be run at some requested frequency if possible, on the CPUs "
            "selected for the step on the compute node(s)."
        ),
    )
    cpus_per_gpu: Optional[str] = Field(description="Number of CPUs requested per allocated GPU.")
    cpus_per_task: Optional[int] = Field(
        description=(
            "Advise the Slurm controller that ensuing job steps will require "
            "ncpus number of processors per task."
        ),
    )
    current_working_directory: Optional[str] = Field(
        description="Instruct Slurm to connect the batch script's standard output directly to the file name."
    )
    deadline: Optional[str] = Field(
        description=(
            "Remove the job if no ending is possible before this deadline (start > (deadline - time[-min]))."
        )
    )
    delay_boot: Optional[int] = Field(
        description=(
            "Do not reboot nodes in order to satisfied this job's feature specification if "
            "the job has been eligible to run for less than this time period."
        )
    )
    dependency: Optional[str] = Field(
        description=(
            "Defer the start of this job until the specified dependencies have been satisfied completed."
        )
    )
    distribution: Optional[str] = Field(
        description="Specify alternate distribution methods for remote processes."
    )
    environment: Optional[Dict[str, str]] = Field(description="Dictionary of environment entries.")
    exclusive: Optional[Literal["user", "mcs", "exclusive", "oversubscribe"]] = Field(
        description=(
            "The job allocation can share nodes just other users with the "
            "'user' option or with the 'mcs' option)."
        )
    )
    get_user_environment: int = Field(
        default=1,
        description="Load new login environment for user on job node.",
        ge=0,
        le=1,
    )
    gres: Optional[str] = Field(
        description="Specifies a comma delimited list of generic consumable resources."
    )
    gres_flags: Optional[Literal["disable-binding", "enforce-binding"]] = Field(
        description="Specify generic resource task binding options."
    )
    gpu_binding: Optional[str] = Field(description="Requested binding of tasks to GPU.")
    gpu_frequency: Optional[str] = Field(description="Requested GPU frequency.")
    gpus: Optional[str] = Field(description="GPUs per job.")
    gpus_per_node: Optional[str] = Field(description="GPUs per node.")
    gpus_per_socket: Optional[str] = Field(description="GPUs per socket.")
    gpus_per_task: Optional[str] = Field(description="GPUs per task.")
    hold: Optional[bool] = Field(
        description="Specify the job is to be submitted in a held state (priority of zero)."
    )
    kill_on_invalid_dependency: Optional[bool] = Field(
        description="If a job has an invalid dependency, then Slurm is to terminate it."
    )
    licenses: Optional[str] = Field(
        description=(
            "Specification of licenses (or other resources available on all nodes of the cluster) "
            "which must be allocated to this job."
        )
    )
    mail_type: Optional[str] = Field(description="Notify user by email when certain event types occur.")
    mail_user: Optional[str] = Field(
        description="User to receive email notification of state changes as defined by mail_type."
    )
    mcs_label: Optional[str] = Field(description="This parameter is a group among the groups of the user.")
    memory_binding: Optional[str] = Field(description="Bind tasks to memory.")
    memory_per_cpu: Optional[int] = Field(description="Minimum real memory per cpu (MB).")
    memory_per_gpu: Optional[int] = Field(description="Minimum memory required per allocated GPU.")
    memory_per_node: Optional[str] = Field(description="Minimum real memory per node (MB).")
    minimum_cpus_per_node: Optional[int] = Field(description="Minimum number of CPUs per node.")
    minimum_nodes: Optional[bool] = Field(
        description="If a range of node counts is given, prefer the smaller count."
    )
    name: Optional[str] = Field(description="Specify a name for the job allocation.")
    nice: Optional[str] = Field(description="Run the job with an adjusted scheduling priority within Slurm.")
    no_kill: Optional[bool] = Field(
        description="Do not automatically terminate a job if one of the nodes it has been allocated fails."
    )
    nodes: Optional[str] = Field(
        description="Request that a minimum of nodes nodes and a maximum node count.",
    )
    open_mode: Optional[Literal["append", "truncate"]] = Field(
        description="Open the output and error files using append or truncate mode as specified."
    )
    partition: Optional[str] = Field(description="Request a specific partition for the resource allocation.")
    priority: Optional[str] = Field(description="Request a specific job priority.")
    qos: Optional[str] = Field(description="Request a quality of service for the job.")
    requeue: Optional[bool] = Field(
        description="Specifies that the batch job should eligible to being requeue."
    )
    reservation: Optional[str] = Field(
        description="Allocate resources for the job from the named reservation."
    )
    signal: Optional[str] = Field(
        description="When a job is within sig_time seconds of its end time, send it the signal sig_num.",
    )
    sockets_per_node: Optional[int] = Field(
        description="Restrict node selection to nodes with at least the specified number of sockets."
    )
    spread_job: Optional[bool] = Field(
        description=(
            "Spread the job allocation over as many nodes as possible and attempt "
            "to evenly distribute tasks across the allocated nodes."
        )
    )
    standard_error: Optional[str] = Field(
        description="Instruct Slurm to connect the batch script's standard error directly to the file name."
    )
    standard_input: Optional[str] = Field(
        description=(
            "Instruct Slurm to connect the batch script's standard input directly to the file name specified."
        )
    )
    standard_output: Optional[str] = Field(
        description="Instruct Slurm to connect the batch script's standard output directly to the file name."
    )
    tasks: Optional[int] = Field(
        description=(
            "Advises the Slurm controller that job steps run within the allocation "
            "will launch a maximum of number tasks and to provide for sufficient resources."
        )
    )
    tasks_per_core: Optional[int] = Field(description="Request the maximum ntasks be invoked on each core.")
    tasks_per_node: Optional[int] = Field(description="Request the maximum ntasks be invoked on each node.")
    tasks_per_socket: Optional[int] = Field(
        description="Request the maximum ntasks be invoked on each socket."
    )
    thread_specification: Optional[int] = Field(
        description=(
            "Count of specialized threads per node reserved by the job for system "
            "operations and not used by the application."
        )
    )
    threads_per_core: Optional[int] = Field(
        description="Restrict node selection to nodes with at least the specified number of threads per core."
    )
    time_limit: Optional[str] = Field(description="Step time limit.")
    time_minimum: Optional[int] = Field(description="Minimum run time in minutes.")
    wait_all_nodes: Optional[int] = Field(
        description="Do not begin execution until all nodes are ready for use.", ge=0, le=1
    )
    wckey: Optional[str] = Field(description="Specify wckey to be used with job.")


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    job_submission_name: str
    job_submission_description: Optional[str]
    job_script_id: int
    execution_directory: Optional[Path]
    client_id: Optional[str]
    execution_parameters: JobProperties = Field(default_factory=JobProperties)

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionUpdateRequest(BaseModel):
    """
    Request model for updating JobSubmission instances.
    """

    job_submission_name: Optional[str]
    job_submission_description: Optional[str]
    execution_directory: Optional[Path]
    status: Optional[JobSubmissionStatus]

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionResponse(BaseModel):
    """
    Complete model to match the database for the JobSubmission resource.
    """

    id: Optional[int] = Field(None)
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    job_submission_name: str
    job_submission_description: Optional[str]
    job_submission_owner_email: str
    job_script_id: int
    execution_directory: Optional[Path]
    slurm_job_id: Optional[int]
    client_id: Optional[str]
    status: JobSubmissionStatus
    report_message: Optional[str]
    execution_parameters: Optional[JobProperties]

    class Config:
        orm_mode = True
        schema_extra = job_submission_meta_mapper


class PendingJobSubmission(BaseModel, extra=Extra.ignore):
    """
    Specialized model for the cluster-agent to pull pending job_submissions.

    Model also includes data from its job_script and application sources.
    """

    id: Optional[int] = Field(None)
    job_submission_name: str
    job_submission_owner_email: str
    execution_directory: Optional[Path]
    execution_parameters: Dict = Field(default_factory=dict)
    job_script_name: str
    application_name: str
    job_script_files: JobScriptFiles


class ActiveJobSubmission(BaseModel, extra=Extra.ignore):
    """
    Specialized model for the cluster-agent to pull an active job_submission.
    """

    id: int
    job_submission_name: str
    slurm_job_id: int
