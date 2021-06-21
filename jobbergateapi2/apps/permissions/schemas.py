"""
Defines the schema for the permissions resources.
"""
from typing import Optional

from pydantic import BaseModel, Field

_ACL_RX = r"^(Allow|Deny)\|(role:\w+|Authenticated)\|\w+$"
_RESOURCE_RX = r"^(application|job_script|job_submission)$"


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


class JobScriptPermission(BasePermission):
    """
    Permission model for the JobScript resource.
    """


class JobSubmissionPermission(BasePermission):
    """
    Permission model for the JobSubmission resource.
    """


class AllPermissions(BasePermission):
    """
    Schema to return all permissions.
    """

    resource_name: str = Field(..., regex=_RESOURCE_RX)
