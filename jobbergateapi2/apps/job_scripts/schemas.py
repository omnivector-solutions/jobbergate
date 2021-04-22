"""
Defines the schema for the JobScript resource
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobScript(BaseModel):
    """
    Model for the resource JobScript
    """

    id: Optional[int] = Field(None)
    job_script_name: str = Field(...)
    job_script_description: Optional[str] = Field("")
    job_script_data_as_string: str = Field(...)
    job_script_owner_id: int = Field(..., description="The User id of the owner")
    job_script_application_id: int = Field(..., description="The Application id")
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())

    class Config:
        orm_mode = True

    def __str__(self):
        return self.job_script_name
