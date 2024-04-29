"""
Provide a module that describes permissions in the API.
"""

from enum import Enum


class Permissions(str, Enum):
    """
    Describe the permissions that may be used for protecting Jobbergate routes.
    """

    ADMIN = "jobbergate:admin"
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
