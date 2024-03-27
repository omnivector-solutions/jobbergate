import sys
from pathlib import Path
from typing import Optional

import buzz
from pydantic import AnyHttpUrl, BaseSettings, Field, root_validator
from pydantic.error_wrappers import ValidationError

from jobbergate_agent.utils.logging import logger


class Settings(BaseSettings):
    # Sbatch
    SBATCH_PATH: Path = Path("/usr/bin/sbatch")
    SCONTROL_PATH: Path = Path("/usr/bin/scontrol")
    X_SLURM_USER_NAME: str = "ubuntu"
    DEFAULT_SLURM_WORK_DIR: Path = Path("/tmp")

    # cluster api info
    BASE_API_URL: AnyHttpUrl = Field("https://armada-k8s.staging.omnivector.solutions")

    # Sentry
    SENTRY_DSN: Optional[AnyHttpUrl] = None
    SENTRY_ENV: str = "local"

    # OIDC config for machine-to-machine security
    OIDC_DOMAIN: str
    OIDC_AUDIENCE: str = "https://apis.omnivector.solutions"
    OIDC_CLIENT_ID: str
    OIDC_CLIENT_SECRET: str
    OIDC_USE_HTTPS: bool = True

    CACHE_DIR = Path.home() / ".cache/jobbergate-agent"
    REQUESTS_TIMEOUT: Optional[int] = 15

    # Type of slurm user mapper to use
    SLURM_USER_MAPPER: Optional[str]

    # Single user submitter settings
    SINGLE_USER_SUBMITTER: Optional[str]

    # Task settings
    TASK_JOBS_INTERVAL_SECONDS: int = Field(60, ge=10, le=3600)  # seconds
    TASK_GARBAGE_COLLECTION_HOUR: Optional[int] = Field(None, ge=0, le=23)  # hour of day
    TASK_SELF_UPDATE_INTERVAL_SECONDS: int = Field(60 * 60, ge=10)  # seconds

    # Job submission settings
    WRITE_SUBMISSION_FILES: bool = True

    @root_validator
    def compute_extra_settings(cls, values):
        """
        Compute settings values that are based on other settings values.
        """
        buzz.require_condition(
            values["SBATCH_PATH"].is_absolute(),
            "SBATCH_PATH must be an absolute path to an existing file",
            ValueError,
        )
        buzz.require_condition(
            values["SCONTROL_PATH"].is_absolute(),
            "SCONTROL_PATH must be an absolute path to an existing file",
            ValueError,
        )

        # If using single user, but don't have the setting, use default slurm user
        if values["SINGLE_USER_SUBMITTER"] is None:
            values["SINGLE_USER_SUBMITTER"] = values["X_SLURM_USER_NAME"]

        return values

    class Config:
        """
        Provide configuration for the project settings.

        Note that we disable use of ``dotenv`` if we are in test mode.
        """

        env_prefix = "JOBBERGATE_AGENT_"

        _test_mode = "pytest" in sys.modules
        if not _test_mode:
            env_file = ".env"


def init_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logger.error(e)
        sys.exit(1)


SETTINGS = init_settings()
