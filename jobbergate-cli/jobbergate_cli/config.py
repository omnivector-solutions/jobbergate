"""
Configuration file, sets all the necessary environment variables.
Can load configuration from a dotenv file if supplied.
"""

from pathlib import Path
from sys import exit
from typing import Optional

from pydantic import Field, ValidationError, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobbergate_cli import constants
from jobbergate_cli.constants import OV_CONTACT
from jobbergate_cli.render import terminal_message
from jobbergate_cli.text_tools import conjoin


def _get_env_file() -> Path:
    """
    Load the env file based on the constant JOBBERGATE_DEFAULT_DOTENV_PATH if the file exists. Otherwise use ".env".
    """
    env_file: Path
    if constants.JOBBERGATE_DEFAULT_DOTENV_PATH.is_file():
        env_file = constants.JOBBERGATE_DEFAULT_DOTENV_PATH
    else:
        env_file = Path(".env")
    return env_file


class Settings(BaseSettings):
    """
    Provide a ``pydantic`` settings model to hold configuration values loaded from the environment.
    """

    JOBBERGATE_CACHE_DIR: Path = Field(Path.home() / ".local/share/jobbergate3")

    ARMADA_API_BASE: str = Field("https://apis.vantagecompute.ai")

    SBATCH_PATH: Optional[Path] = None

    # enable http tracing
    JOBBERGATE_DEBUG: bool = Field(False)
    JOBBERGATE_REQUESTS_TIMEOUT: Optional[int] = 15

    # Setry's configuration
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACE_RATE: float = Field(1.0, gt=0.0, le=1.0)
    SENTRY_ENV: str = "LOCAL"

    # Default job submission cluster
    DEFAULT_CLUSTER_NAME: Optional[str] = None

    # How long it will use cached cluster lists before fetching them again
    JOBBERGATE_CLUSTER_CACHE_LIFETIME: int = 60 * 5

    # Settings for log uploads
    JOBBERGATE_AWS_ACCESS_KEY_ID: Optional[str] = None
    JOBBERGATE_AWS_SECRET_ACCESS_KEY: Optional[str] = None
    JOBBERGATE_S3_LOG_BUCKET: str = Field("jobbergate-cli-logs")

    # Compatibility mode: If True, add commands as they appear in the legacy app
    JOBBERGATE_COMPATIBILITY_MODE: Optional[bool] = False
    JOBBERGATE_LEGACY_NAME_CONVENTION: Optional[bool] = False

    # Auth0 config for machine-to-machine security
    OIDC_DOMAIN: str = "auth.vantagecompute.ai/realms/vantage"
    OIDC_CLIENT_ID: str = "default"
    OIDC_USE_HTTPS: bool = True
    OIDC_CLIENT_SECRET: Optional[str] = None

    @field_validator("JOBBERGATE_CACHE_DIR", mode="after")
    def _validate_cache_dir(cls, value: Path) -> Path:
        """
        Expand, resolve, and create cache directory.
        """
        value = value.expanduser().resolve()
        value.mkdir(exist_ok=True, parents=True)
        return value

    @computed_field
    def JOBBERGATE_USER_TOKEN_DIR(self) -> Path:
        token_dir = self.JOBBERGATE_CACHE_DIR / "token"
        token_dir.mkdir(exist_ok=True, parents=True)
        return token_dir

    @computed_field
    def JOBBERGATE_LOG_PATH(self) -> Path:
        log_file = self.JOBBERGATE_CACHE_DIR / "logs" / "jobbergate-cli.log"
        log_file.parent.mkdir(exist_ok=True, parents=True)
        return log_file

    @computed_field
    def JOBBERGATE_APPLICATION_MODULE_PATH(self) -> Path:
        return self.JOBBERGATE_CACHE_DIR / constants.JOBBERGATE_APPLICATION_MODULE_FILE_NAME

    @computed_field
    def JOBBERGATE_APPLICATION_CONFIG_PATH(self) -> Path:
        return self.JOBBERGATE_CACHE_DIR / constants.JOBBERGATE_APPLICATION_CONFIG_FILE_NAME

    @computed_field
    def JOBBERGATE_CLUSTER_LIST_PATH(self) -> Path:
        return self.JOBBERGATE_CACHE_DIR / "clusters.json"

    @property
    def is_onsite_mode(self) -> bool:
        """Check if the SBATCH_PATH is set, indicating that the CLI is running in on-site mode."""
        return self.SBATCH_PATH is not None

    model_config = SettingsConfigDict(env_file=_get_env_file(), extra="ignore")


def build_settings(*args, **kwargs):
    """
    Return a Setting object and handle ValidationError with a message to the user.
    """
    try:
        return Settings(*args, **kwargs)
    except ValidationError as err:
        terminal_message(
            conjoin(
                "A configuration error was detected.",
                "",
                f"[yellow]Please contact [bold]{OV_CONTACT}[/bold] for support and trouble-shooting[/yellow]",
                "",
                "Details:",
                "",
                f"[red]{err}[/red]",
            ),
            subject="Configuration Error",
        )
        exit(1)


settings = build_settings()
