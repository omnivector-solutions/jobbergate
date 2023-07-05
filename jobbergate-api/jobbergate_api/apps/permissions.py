"""
Provide a module that describes permissions in the API.
"""

from enum import Enum


class Permissions(str, Enum):
    """
    Describe the permissions that may be used for protecting Jobbergate routes.
    """

    JOB_TEMPLATES_VIEW = "jobbergate:job-templates:view"
    JOB_TEMPLATES_EDIT = "jobbergate:job-templates:edit"
    JOB_SCRIPTS_VIEW = "jobbergate:job-scripts:view"
    JOB_SCRIPTS_EDIT = "jobbergate:job-scripts:edit"
    JOB_SUBMISSIONS_VIEW = "jobbergate:job-submissions:view"
    JOB_SUBMISSIONS_EDIT = "jobbergate:job-submissions:edit"
