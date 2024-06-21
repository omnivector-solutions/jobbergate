"""
Configuration file, sets all the necessary environment variables.
Can load configuration from a dotenv file if supplied.
"""

from pathlib import Path
from sys import exit
from typing import Optional

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

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

    ARMADA_API_BASE: str = Field("https://armada-k8s.staging.omnivector.solutions")

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

    # Computed values. Listed as Optional, but will *always* be set (or overridden) based on other values
    JOBBERGATE_APPLICATION_MODULE_PATH: Optional[Path] = None
    JOBBERGATE_APPLICATION_CONFIG_PATH: Optional[Path] = None
    JOBBERGATE_LOG_PATH: Optional[Path] = None
    JOBBERGATE_USER_TOKEN_DIR: Optional[Path] = None
    JOBBERGATE_ACCESS_TOKEN_PATH: Optional[Path] = None
    JOBBERGATE_REFRESH_TOKEN_PATH: Optional[Path] = None

    JOBBERGATE_CLUSTER_LIST_PATH: Optional[Path] = None

    # Compatibility mode: If True, add commands as they appear in the legacy app
    JOBBERGATE_COMPATIBILITY_MODE: Optional[bool] = False
    JOBBERGATE_LEGACY_NAME_CONVENTION: Optional[bool] = False

    # Auth0 config for machine-to-machine security
    OIDC_DOMAIN: str
    OIDC_AUDIENCE: str
    OIDC_CLIENT_ID: str
    OIDC_USE_HTTPS: bool = True
    OIDC_MAX_POLL_TIME: int = 5 * 60  # 5 Minutes

    # Enable multi-tenancy to fix cluster name mapping by client_id
    MULTI_TENANCY_ENABLED: bool = False

    @model_validator(mode="after")
    def compute_extra_settings(self) -> Self:
        """
        Compute settings values that are based on other settings values.
        """
        self.JOBBERGATE_CACHE_DIR = Path(self.JOBBERGATE_CACHE_DIR).expanduser().resolve()
        cache_dir = self.JOBBERGATE_CACHE_DIR
        cache_dir.mkdir(exist_ok=True, parents=True)

        self.JOBBERGATE_APPLICATION_MODULE_PATH = cache_dir / constants.JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        self.JOBBERGATE_APPLICATION_CONFIG_PATH = cache_dir / constants.JOBBERGATE_APPLICATION_CONFIG_FILE_NAME

        log_dir = cache_dir / "logs"
        log_dir.mkdir(exist_ok=True, parents=True)
        self.JOBBERGATE_LOG_PATH = log_dir / "jobbergate-cli.log"

        token_dir = cache_dir / "token"
        token_dir.mkdir(exist_ok=True, parents=True)
        self.JOBBERGATE_USER_TOKEN_DIR = token_dir
        self.JOBBERGATE_ACCESS_TOKEN_PATH = token_dir / "access.token"
        self.JOBBERGATE_REFRESH_TOKEN_PATH = token_dir / "refresh.token"

        self.JOBBERGATE_CLUSTER_LIST_PATH = cache_dir / "clusters.json"

        return self

    @property
    def is_onsite_mode(self) -> bool:
        """Check if the SBATCH_PATH is set, indicating that the CLI is running in on-site mode."""
        return self.SBATCH_PATH is not None

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
    )


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
