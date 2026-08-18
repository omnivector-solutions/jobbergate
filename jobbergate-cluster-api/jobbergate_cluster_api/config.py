"""
Configuration for the Jobbergate Cluster API, loaded from the environment.

All variables are prefixed with ``CLUSTER_API_`` (e.g. ``CLUSTER_API_ARMASEC_DOMAIN``).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Provide a ``pydantic`` settings model to hold configuration values loaded from the environment.
    """

    DEPLOY_ENV: str = "LOCAL"
    LOG_LEVEL: str = "DEBUG"

    # Auth (same OIDC provider and permission model as the cloud jobbergate-api)
    ARMASEC_DOMAIN: str = "keycloak.local:8080/realms/jobbergate-local"
    ARMASEC_USE_HTTPS: bool = False
    ARMASEC_DEBUG: bool = False

    # Where per-session working directories live. Must be on a filesystem shared
    # with the compute nodes of the sessions partition (e.g. NFS).
    SESSIONS_DIR: Path = Path("/nfs/cluster-api-sessions")

    # Slurm integration
    SESSIONS_PARTITION: str = "interactive"
    SBATCH_PATH: Path = Path("/usr/bin/sbatch")
    SCONTROL_PATH: Path = Path("/usr/bin/scontrol")
    SCANCEL_PATH: Path = Path("/usr/bin/scancel")
    # Local unix user the session job is submitted as (via gosu when running as root).
    # Production deployments should replace this with a real user mapper (see README).
    SUBMIT_USER: str = "local-user"

    # The cluster this API serves; forwarded to the CLI for on-site submission.
    CLUSTER_NAME: str = "local-slurm"

    # Environment handed to the jobbergate-cli process inside the session
    CLI_BASE_API_URL: str = "http://jobbergate-api:80"
    CLI_OIDC_DOMAIN: str = "keycloak.local:8080/realms/jobbergate-local"
    CLI_OIDC_CLIENT_ID: str = "cli"
    CLI_OIDC_USE_HTTPS: bool = False

    # How the session job launches the CLI. APP_DIR is the mounted uv workspace root.
    APP_DIR: Path = Path("/app")
    UV_CACHE_DIR: Path = Path("/nfs/.uv-cache")
    UV_ENV_DIR: Path = Path("/nfs/.venvs/jobbergate-cli")

    # Public base path this API is served under; ttyd is started with a matching
    # --base-path so the terminal page's relative asset/websocket URLs survive proxying.
    BASE_PATH: str = "/jobbergate/sessions"

    model_config = SettingsConfigDict(env_prefix="CLUSTER_API_", env_file=".env", extra="ignore")


settings = Settings()
