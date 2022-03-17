"""
Provide a module that describes permissions in the API.
"""

from enum import Enum


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
