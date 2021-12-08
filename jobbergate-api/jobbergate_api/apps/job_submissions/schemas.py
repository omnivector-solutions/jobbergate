"""
JobSubmission resource schema.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobSubmissionRequest(BaseModel):
    """
    Request model for the JobSubmission resource.
    """

    job_submission_name: str = Field(...)
    job_submission_description: Optional[str] = Field("")
    job_script_id: int = Field(..., description="The JobScript id")
    slurm_job_id: Optional[int] = Field(None)

    class Config:
        orm_mode = True
        # Provides an example on the swagger pages. See:
        # https://fastapi.tiangolo.com/tutorial/schema-extra-example/#pydantic-schema_extra
        schema_extra = {"example": {"job_submission_name": "name", "job_script_id": 1}}

    def __str__(self):
        return self.job_submission_name


class JobSubmission(JobSubmissionRequest):
    """
    Complete model to match the database for the JobSubmission resource.
    """

    id: Optional[int] = Field(None)
    job_submission_owner_email: str = Field(...)
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())
