"""
JobScript resource schema.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobScriptRequest(BaseModel):
    """
    Request model for the JobScript resource.
    """

    job_script_name: str = Field(...)
    job_script_description: Optional[str] = Field("")
    job_script_data_as_string: str = Field(...)
    job_script_owner_email: str = Field(..., description="The email address of the owner")
    application_id: int = Field(..., description="The Application id")

    class Config:
        orm_mode = True

    def __str__(self):
        return self.job_script_name


class JobScript(JobScriptRequest):
    """
    Complete model to match database for the JobScript resource.
    """

    id: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())
