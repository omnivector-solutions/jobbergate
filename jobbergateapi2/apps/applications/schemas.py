"""
Defines the schema for the resource Application.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationRequest(BaseModel):
    """
    Request model for the Application resource.
    """

    application_name: str = Field(...)
    application_description: Optional[str] = Field("")
    application_owner_id: Optional[int] = Field(None, description="The User id of the owner")
    application_file: str = Field(..., description="Application file content (.py) as text")
    application_config: str = Field(..., description="Application config file content (.yaml) as text")

    class Config:
        orm_mode = True

    def __str__(self):
        return self.application_name


class Application(ApplicationRequest):
    """
    Complete model to match the database for the Application resource.
    """

    id: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())
