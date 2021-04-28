"""
JobSubmission resource schema.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobSubmission(BaseModel):
    """
    Model for the resource JobSubmission
    """

    id: Optional[int] = Field(None)
    job_submission_name: str = Field(...)
    job_submission_description: Optional[str] = Field("")
    job_submission_owner_id: int = Field(...)
    job_script_id: int = Field(..., description="The JobScript id")
    slurm_job_id: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())

    class Config:
        orm_mode = True

    def __str__(self):
        return self.job_submission_name
