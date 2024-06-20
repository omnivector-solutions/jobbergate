import sys
from pathlib import Path
from typing import Optional

import buzz
from pydantic import AnyHttpUrl, Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

from jobbergate_agent.utils.logging import logger


def _get_env_file() -> str | None:
    """
    Determine if running in test mode and return the correct path to the .env file if not.
    """
    _test_mode = "pytest" in sys.modules
    env_file: str | None
    if not _test_mode:
        env_file = ".env"
    else:
        env_file = None
    return env_file


class Settings(BaseSettings):
    # Sbatch
    SBATCH_PATH: Path = Path("/usr/bin/sbatch")
    SCONTROL_PATH: Path = Path("/usr/bin/scontrol")
    X_SLURM_USER_NAME: str = "ubuntu"
    DEFAULT_SLURM_WORK_DIR: Path = Path("/tmp")

    # cluster api info
    BASE_API_URL: str = "https://armada-k8s.staging.omnivector.solutions"

    # Sentry
    SENTRY_DSN: Optional[AnyHttpUrl] = None
    SENTRY_ENV: str = "local"

    # OIDC config for machine-to-machine security
    OIDC_DOMAIN: str
    OIDC_AUDIENCE: str = "https://apis.omnivector.solutions"
    OIDC_CLIENT_ID: str
    OIDC_CLIENT_SECRET: str
    OIDC_USE_HTTPS: bool = True

    CACHE_DIR: Path = Path.home() / ".cache/jobbergate-agent"
    REQUESTS_TIMEOUT: Optional[int] = 15

    # Type of slurm user mapper to use
    SLURM_USER_MAPPER: Optional[str] = None

    # Single user submitter settings
    SINGLE_USER_SUBMITTER: Optional[str] = None

    # Task settings
    TASK_JOBS_INTERVAL_SECONDS: int = Field(60, ge=10, le=3600)  # seconds
    TASK_GARBAGE_COLLECTION_HOUR: Optional[int] = Field(None, ge=0, le=23)  # hour of day
    TASK_SELF_UPDATE_INTERVAL_SECONDS: Optional[int] = Field(None, ge=10)  # seconds

    # Job submission settings
    WRITE_SUBMISSION_FILES: bool = True

    @model_validator(mode="after")
    def compute_extra_settings(self) -> Self:
        """
        Compute settings values that are based on other settings values.
        """
        buzz.require_condition(
            self.SBATCH_PATH.is_absolute(),
            "SBATCH_PATH must be an absolute path to an existing file",
            ValueError,
        )
        buzz.require_condition(
            self.SCONTROL_PATH.is_absolute(),
            "SCONTROL_PATH must be an absolute path to an existing file",
            ValueError,
        )

        # If using single user, but don't have the setting, use default slurm user
        if self.SINGLE_USER_SUBMITTER is None:
            self.SINGLE_USER_SUBMITTER = self.X_SLURM_USER_NAME
        return self

    model_config = SettingsConfigDict(
        env_prefix="JOBBERGATE_AGENT_",
        env_file=_get_env_file(),
    )


def init_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logger.error(e)
        sys.exit(1)


SETTINGS = init_settings()
