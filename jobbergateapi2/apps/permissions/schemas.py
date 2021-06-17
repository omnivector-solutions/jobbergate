"""
Defines the schema for the permissions resources.
"""
from typing import Optional

from pydantic import BaseModel, Field

_ACL_RX = r"^(Allow|Deny)\|(role:\w+|Authenticated)\|\w+$"


class BasePermission(BaseModel):
    """
    Base model for the Permission resource.
    """

    id: Optional[int] = Field(None)
    acl: str = Field(..., regex=_ACL_RX)

    class Config:
        orm_mode = True

    def __str__(self):
        return self.acl


class ApplicationPermission(BasePermission):
    """
    Permission model for the Application resource.
    """
