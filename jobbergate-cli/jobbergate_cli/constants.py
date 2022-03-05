"""
Constants used throughout the tool
"""
from pathlib import Path

from auto_name_enum import AutoNameEnum, auto


JOBBERGATE_APPLICATION_CONFIG = {
    "application_name": "",
    "application_description": "",
    "application_file": "",
    "application_config": "",
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

JOBBERGATE_DEFAULT_DOTENV_PATH = Path("/etc/default/jobbergate-cli")
JOBBERGATE_APPLICATION_MODULE_FILE_NAME = "jobbergate.py"
JOBBERGATE_APPLICATION_CONFIG_FILE_NAME = "jobbergate.yaml"
TAR_NAME = "jobbergate.tar.gz"

DEFAULT_MAX_BYTES_DEBUG = 1000

OV_CONTACT = "Omnivector Solutions <info@omnivector.solutions>"


class SortOrder(AutoNameEnum):
    """
    Enum descring the type of sort orders that are available for list commands.
    """

    ASCENDING = auto()
    DESCENDING = auto()
    UNSORTED = auto()
