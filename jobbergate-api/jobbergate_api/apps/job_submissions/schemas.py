"""
JobSubmission resource schema.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    execution_duirectory=MetaField(
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
)


class JobProperties(BaseModel, extra=Extra.ignore):
    """
    Specialized model for job properties.

    See more details at: https://slurm.schedmd.com/rest_api.html#v0.0.38_job_properties
    """

    account: Optional[str]
    account_gather_frequency: Optional[str]
    argv: Optional[List[str]]
    array: Optional[str]
    batch_features: Optional[str]
    begin_time: Optional[int]
    burst_buffer: Optional[str]
    cluster_constraints: Optional[str]
    comment: Optional[str]
    constrains: Optional[str]
    containers: Optional[str]
    core_specification: Optional[int]
    cores_per_socket: Optional[int]
    cpu_binding: Optional[str]
    cpu_binding_hint: Optional[str]
    cpu_frequency: Optional[str]
    cpus_per_gpu: Optional[str]
    cpus_per_task: Optional[int]
    current_working_directory: Optional[str]
    deadline: Optional[str]
    delay_boot: Optional[int]
    dependency: Optional[str]
    distribution: Optional[str]
    environment: Optional[Dict[Any, Any]]
    exclusive: Optional[str]
    get_user_environment: Optional[bool]
    gress: Optional[str]
    gress_flags: Optional[str]
    gpu_binding: Optional[str]
    gpu_frequency: Optional[str]
    gpus: Optional[str]
    gpus_per_node: Optional[str]
    gpus_per_socket: Optional[str]
    gpus_per_task: Optional[str]
    hold: Optional[bool]
    kill_on_invalid_dependency: Optional[bool]
    licenses = Optional[str]
    mail_type: Optional[str]
    mail_user: Optional[str]
    mcs_label: Optional[str]
    memory_binding: Optional[int]
    memory_per_gpu: Optional[int]
    memory_per_node: Optional[int]
    minimum_cpus_per_note: Optional[int]
    minimum_nodes: Optional[bool]
    name: Optional[str]
    nice: Optional[str]
    no_kill: Optional[bool]
    nodes: Optional[List[int]]
    open_mode: Optional[str]
    partition: Optional[str]
    priority: Optional[str]
    qos: Optional[str]
    requeue: Optional[bool]
    reservation: Optional[str]
    signal: Optional[str]
    sockets_per_node: Optional[int]
    spread_job: Optional[bool]
    standard_error: Optional[str]
    standard_input: Optional[str]
    standard_output: Optional[str]
    tasks: Optional[int]
    tasks_per_core: Optional[int]
    tasks_per_node: Optional[int]
    tasks_per_socket: Optional[int]
    thread_specification: Optional[int]
    threads_per_core: Optional[int]
    time_limit: Optional[int]
    time_minimum: Optional[int]
    wait_all_nodes: Optional[bool]
    wckey: Optional[str]


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    job_submission_name: str
    job_submission_description: Optional[str]
    job_script_id: int
    execution_directory: Optional[Path]
    client_id: Optional[str]
    execution_parameters: Optional[JobProperties]

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
