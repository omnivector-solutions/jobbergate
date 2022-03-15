"""
JobSubmission resource schema.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Extra, Field

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_submission_meta_mapper = MetaMapper(
    id=MetaField(description="The unique database identifier for the instance", example=101,),
    created_at=MetaField(
        description="The timestamp for when the instance was created", example="2021-12-28 23:13:00",
    ),
    updated_at=MetaField(
        description="The timestamp for when the instance was last updated", example="2021-12-28 23:52:00",
    ),
    job_submission_name=MetaField(
        description="The unique name of the job submission", example="test-job-submission-77",
    ),
    job_submission_description=MetaField(
        description="A text field providing a human-friendly description of the job_submission",
        example="Submission for the Foo job on sample 99 using the bar variant",
    ),
    job_submission_owner_email=MetaField(
        description="The email of the owner/creator of the instance", example="tucker@omnivector.solutions",
    ),
    job_script_id=MetaField(
        description="The foreign-key to the job_script from which this instance was created", example=71,
    ),
    slurm_job_id=MetaField(
        description="The id for the slurm job executing this job_submission", example="1883",
    ),
    cluster_client_id=MetaField(
        description="The client_id of the cluster where this job submission should execute",
        example="D9p5eD9lEVj7S6h7hXAYoOAnrITSbmOK",
    ),
    status=MetaField(
        description=f"The status of the job submission. Must be one of {JobSubmissionStatus.pretty_list()}",
        example=JobSubmissionStatus.CREATED,
    ),
)


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    job_submission_name: str
    job_submission_description: Optional[str]
    job_script_id: int
    slurm_job_id: Optional[int]
    cluster_client_id: Optional[str]

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionUpdateRequest(BaseModel):
    """
    Request model for updating JobSubmission instances.
    """

    job_submission_name: Optional[str]
    job_submission_description: Optional[str]
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
    slurm_job_id: Optional[int]
    cluster_client_id: Optional[str]
    status: JobSubmissionStatus

    class Config:
        orm_mode = True
        schema_extra = job_submission_meta_mapper


class PendingJobSubmission(BaseModel, extra=Extra.ignore):
    """
    Specialized model for the cluster-agent to pull a pending job_submission along with
    data from its job_script and application sources.
    """

    id: Optional[int] = Field(None)
    job_submission_name: str
    job_script_name: str
    job_script_data_as_string: str
    application_name: str
