import sys
from pathlib import Path
from typing import Optional

import buzz
from pydantic import AnyHttpUrl, Field, ValidationError, model_validator, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

from jobbergate_agent.utils.logging import logger


def _get_env_file() -> Path | None:
    """
    Determine if running in test mode and return the correct path to the .env file if not.
    """
    _test_mode = "pytest" in sys.modules
    if not _test_mode:
        default_dotenv_file_location = Path("/var/snap/jobbergate-agent/common/.env")
        if default_dotenv_file_location.exists():
            return default_dotenv_file_location
        return Path(".env")
    return None


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

    # InfluxDB settings for job metric collection
    INFLUX_DSN: Optional[AnyUrl] = Field(
        None, description="InfluxDB DSN. Only supports the schemes 'influxdb', 'https+influxdb' and 'udp+influxdb'"
    )
    INFLUX_POOL_SIZE: int = Field(10, ge=1, description="Number of InfluxDB connections to pool")
    INFLUX_SSL: bool = Field(False, description="Use SSL for InfluxDB connection")
    INFLUX_VERIFY_SSL: bool = Field(False, description="Verify SSL certificate for InfluxDB connection")
    INFLUX_TIMEOUT: Optional[int] = Field(None, ge=1, description="Timeout for InfluxDB connection")
    INFLUX_UDP_PORT: int = Field(4444, ge=1, le=65535, description="UDP port for InfluxDB connection")
    INFLUX_CERT_PATH: Optional[Path] = Field(None, description="Path to InfluxDB certificate file")

    @property
    def influx_integration_enabled(self) -> bool:
        return self.INFLUX_DSN is not None

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

    @model_validator(mode="after")
    def validate_influxdb_settings(self) -> Self:
        if self.influx_integration_enabled:
            buzz.require_condition(
                not self.INFLUX_SSL or self.INFLUX_CERT_PATH is not None,
                "INFLUX_CERT_PATH must be provided when INFLUX_SSL is enabled",
                ValueError,
            )

            assert self.INFLUX_DSN is not None  # mypy assertion
            if self.INFLUX_DSN.scheme not in ["influxdb", "https+influxdb", "udp+influxdb"]:
                raise ValueError("INFLUX_DSN scheme must be one of 'influxdb', 'https+influxdb' or 'udp+influxdb'")
        return self

    model_config = SettingsConfigDict(env_prefix="JOBBERGATE_AGENT_", env_file=_get_env_file(), extra="ignore")


def init_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logger.error(e)
        sys.exit(1)


SETTINGS = init_settings()
