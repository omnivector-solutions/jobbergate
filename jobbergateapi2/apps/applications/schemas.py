"""
Defines the schema for the resource Application.
"""
from datetime import datetime
from typing import Optional

from fastapi_permissions import Allow, Authenticated
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

    def __acl__(self):
        """
        Currently returns only a tuple.

        # There is a table 'applications_permissions', with only an acl String column
        # here applications_acl returns a list of strings, each string is separated by |
        # e.g. applications_acl=["Allow|role:admin|view", "Deny|Authenticated|delete"]
        acl_list = []

        for acl in applications_acl:
            action, principal, permission = acl.split("|")
            action_type = Deny
            if action == "Allow":
                action_type = Allow
            principal_type = principal
            if principal == "Authenticated":
                principal_type = Authenticated
            acl_list.append((action_type, principal_type, permission))

        return acl_list
        """
        return [
            (Allow, Authenticated, "view"),
        ]


class Application(ApplicationRequest):
    """
    Complete model to match the database for the Application resource.
    """

    id: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(datetime.utcnow())
    updated_at: Optional[datetime] = Field(datetime.utcnow())
