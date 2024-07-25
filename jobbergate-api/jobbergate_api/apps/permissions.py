"""
Provide a module that describes permissions in the API.
"""

from enum import Enum


class Permissions(str, Enum):
    """
    Describe the permissions that may be used for protecting Jobbergate routes.
    """

    ADMIN = "jobbergate:admin"
    MAINTAINER = "jobbergate:maintainer"
    CLUSTERS_READ = "jobbergate:clusters:read"
    CLUSTERS_UPDATE = "jobbergate:clusters:update"
    JOB_SCRIPTS_CREATE = "jobbergate:job-scripts:create"
    JOB_SCRIPTS_DELETE = "jobbergate:job-scripts:delete"
    JOB_SCRIPTS_READ = "jobbergate:job-scripts:read"
    JOB_SCRIPTS_UPDATE = "jobbergate:job-scripts:update"
    JOB_SUBMISSIONS_CREATE = "jobbergate:job-submissions:create"
    JOB_SUBMISSIONS_DELETE = "jobbergate:job-submissions:delete"
    JOB_SUBMISSIONS_READ = "jobbergate:job-submissions:read"
    JOB_SUBMISSIONS_UPDATE = "jobbergate:job-submissions:update"
    JOB_TEMPLATES_CREATE = "jobbergate:job-templates:create"
    JOB_TEMPLATES_DELETE = "jobbergate:job-templates:delete"
    JOB_TEMPLATES_READ = "jobbergate:job-templates:read"
    JOB_TEMPLATES_UPDATE = "jobbergate:job-templates:update"


def can_bypass_ownership_check(permissions: list[str]) -> bool:
    """
    Determine if the user has permissions that allow them to bypass ownership checks.
    """
    return Permissions.ADMIN in permissions or Permissions.MAINTAINER in permissions
