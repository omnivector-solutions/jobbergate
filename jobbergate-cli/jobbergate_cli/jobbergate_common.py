"""
Constants used throughout the tool
"""
from configparser import ConfigParser
import os
from pathlib import Path
from urllib.parse import urljoin

from dotenv import load_dotenv
import urllib3


if Path("/etc/default/jobbergate-cli").is_file():
    load_dotenv("/etc/default/jobbergate-cli")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# load these two from the environment, with these defaults.
JOBBERGATE_CACHE_DIR = Path(
    os.environ.get("JOBBERGATE_CACHE_DIR", Path.home() / ".local/share/jobbergate")
)
JOBBERGATE_API_ENDPOINT = os.environ.get(
    "JOBBERGATE_API_ENDPOINT",
    "https://jobbergateapi2-staging.omnivector.solutions",
)
# for reference: staging: "https://jobbergate-api-staging-eu-north-1.omnivector.solutions"

# enable http tracing, accepts e.g. "1", "true", "0", "false"
JOBBERGATE_DEBUG = ConfigParser.BOOLEAN_STATES.get(
    os.environ.get("JOBBERGATE_DEBUG", "false").lower()
)

# grab the username and password from the environment if they are set there
JOBBERGATE_USERNAME = os.environ.get("JOBBERGATE_USERNAME")
JOBBERGATE_PASSWORD = os.environ.get("JOBBERGATE_PASSWORD")

# the rest of the strings can be derived
JOBBERGATE_USER_TOKEN_DIR = JOBBERGATE_CACHE_DIR / "token"

JOBBERGATE_API_JWT_PATH = JOBBERGATE_USER_TOKEN_DIR / "jobbergate.token"

JOBBERGATE_API_OBTAIN_TOKEN_ENDPOINT = urljoin(JOBBERGATE_API_ENDPOINT, "token/")

SBATCH_PATH = os.environ.get("SBATCH_PATH", "/usr/bin/sbatch")

JOBBERGATE_APPLICATION_CONFIG = {
    "application_name": "",
    "application_description": "",
    "application_file": "",
    "application_config": "",
}

JOBBERGATE_JOB_SCRIPT_CONFIG = {
    "job_script_name": "",
    "job_script_description": "TEST_DESC",
    "job_script_owner": "",
    "application": "",
}

JOBBERGATE_JOB_SUBMISSION_CONFIG = {
    "job_submission_name": "",
    "job_submission_description": "TEST_DESC",
    "job_submission_owner": "",
    "job_script": "",
}

JOBBERGATE_APPLICATION_MODULE_FILE_NAME = "jobbergate.py"

JOBBERGATE_APPLICATION_CONFIG_FILE_NAME = "jobbergate.yaml"

JOBBERGATE_APPLICATION_MODULE_PATH = (
    JOBBERGATE_CACHE_DIR / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
)

JOBBERGATE_APPLICATION_CONFIG_PATH = (
    JOBBERGATE_CACHE_DIR / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
)

TAR_NAME = "jobbergate.tar.gz"

JOBBERGATE_APPLICATION_MODULE_PATH = (
    JOBBERGATE_CACHE_DIR / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
)

JOBBERGATE_APPLICATION_CONFIG_PATH = (
    JOBBERGATE_CACHE_DIR / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
)

SENTRY_DSN = os.environ.get("SENTRY_DSN")

JOBBERGATE_LOG_PATH = JOBBERGATE_CACHE_DIR / "logs" / "jobbergate-cli.log"

JOBBERGATE_AWS_ACCESS_KEY_ID = os.environ.get("JOBBERGATE_AWS_ACCESS_KEY_ID")
JOBBERGATE_AWS_SECRET_ACCESS_KEY = os.environ.get("JOBBERGATE_AWS_SECRET_ACCESS_KEY")
JOBBERGATE_S3_LOG_BUCKET = os.environ.get(
    "JOBBERGATE_S3_LOG_BUCKET",
    "jobbergate-cli-logs",
)
