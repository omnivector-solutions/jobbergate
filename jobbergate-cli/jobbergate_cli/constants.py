"""
Provide constants that may be used throughout the CLI modules.
"""

from enum import Enum
from pathlib import Path


JOBBERGATE_APPLICATION_CONFIG = {
    "application_name": "",
    "application_description": "",
}

JOBBERGATE_JOB_SCRIPT_CONFIG = {
    "job_script_name": "",
    "job_script_description": "TEST_DESC",
    "job_script_owner_email": "",
    "application_id": "",
}

JOBBERGATE_JOB_SUBMISSION_CONFIG = {
    "job_submission_name": "",
    "job_submission_description": "TEST_DESC",
    "job_submission_owner_email": "",
    "job_script_id": "",
}

JOBBERGATE_DEFAULT_DOTENV_PATH = Path("/etc/default/jobbergate3-cli")
JOBBERGATE_APPLICATION_SUPPORTED_FILES = {".py", ".yaml", ".j2", ".jinja2"}
JOBBERGATE_APPLICATION_MODULE_FILE_NAME = "jobbergate.py"
JOBBERGATE_APPLICATION_CONFIG_FILE_NAME = "jobbergate.yaml"
TAR_NAME = "jobbergate.tar.gz"

OV_CONTACT = "Omnivector Solutions <info@omnivector.solutions>"


class SortOrder(str, Enum):
    """
    Enum descring the type of sort orders that are available for list commands.
    """

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
    UNSORTED = "UNSORTED"
