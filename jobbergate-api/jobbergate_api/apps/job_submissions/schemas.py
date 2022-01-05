"""
JobSubmission resource schema.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

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
)


class JobSubmissionCreateRequest(BaseModel):
    """
    Request model for creating JobSubmission instances.
    """

    job_submission_name: str
    job_submission_description: Optional[str]
    job_submission_owner_email: Optional[str]
    job_script_id: int
    slurm_job_id: Optional[int]

    class Config:
        schema_extra = job_submission_meta_mapper


class JobSubmissionUpdateRequest(BaseModel):
    """
    Request model for updating JobSubmission instances.
    """

    job_submission_name: Optional[str]
    job_submission_description: Optional[str]

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

    class Config:
        orm_mode = True
        schema_extra = job_submission_meta_mapper
