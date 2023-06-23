"""
Provide a module that describes permissions in the API.
"""

from enum import Enum
from typing import Union

from fastapi import HTTPException, status
from loguru import logger
from pydantic import EmailStr


class Permissions(str, Enum):
    """
    Describe the permissions that may be used for protecting Jobbergate routes.
    """

    APPLICATIONS_VIEW = "jobbergate:applications:view"
    APPLICATIONS_EDIT = "jobbergate:applications:edit"
    JOB_SCRIPTS_VIEW = "jobbergate:job-scripts:view"
    JOB_SCRIPTS_EDIT = "jobbergate:job-scripts:edit"
    JOB_SUBMISSIONS_VIEW = "jobbergate:job-submissions:view"
    JOB_SUBMISSIONS_EDIT = "jobbergate:job-submissions:edit"


def check_owner(
    owner_email: Union[str, EmailStr, None],
    requester_email: Union[str, EmailStr, None],
    entity_id: int,
    entity_name: str,
):
    """
    Assert ownership of an entity and raise a 403 exception with message on failure.
    """
    if requester_email != owner_email:
        message = (
            f"User {requester_email} does not own {entity_name} with id={entity_id}. "
            f"Only the {entity_name} owner ({owner_email}) "
            f"can modify this {entity_name}."
        )
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
