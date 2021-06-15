"""
Defines the schema for the resource ApplicationPermission.
"""
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationPermission(BaseModel):
    """
    Request model for the ApplicationPermission resource.
    """

    id: Optional[int] = Field(None)
    acl: str = Field(..., regex=r"^(Allow|Deny)\|(\w+:\w+|Authenticated)\|\w+$")

    class Config:
        orm_mode = True

    def __str__(self):
        return self.acl
