"""
Defines the schema for the resource User
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Application(BaseModel):
    """
    Model for the resource Application
    """

    id: Optional[int] = Field(None)
    application_name: str = Field(...)
    application_description: Optional[str] = Field("")
    application_owner_id: Optional[int] = Field(None, description="The User id of the owner")
    application_file: str
    application_config: str
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())

    class Config:
        orm_mode = True

    def __str__(self):
        return self.application_name
