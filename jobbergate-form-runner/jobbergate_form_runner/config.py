"""Settings for the Form Runner service, loaded from the environment."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values for the Form Runner service."""

    # Armasec / OIDC — mirrors jobbergate-api so the same user tokens work here
    ARMASEC_DOMAIN: str = "keycloak.local:8080/realms/jobbergate-local"
    ARMASEC_USE_HTTPS: bool = False
    ARMASEC_DEBUG: bool = False

    # Public URL of this service, used to build the form links handed to users
    PUBLIC_URL: str = "http://localhost:8010"
    # URL the runner job uses to reach this service's internal bridge (cluster network)
    BRIDGE_URL: str = "http://jobbergate-form-runner:8000"

    # How runner sessions are executed: "slurm" (sbatch on the shared partition) or
    # "subprocess" (a local process; useful for development without a cluster)
    RUNNER_MODE: str = "slurm"
    RUNNER_PARTITION: str = "form"
    RUNNER_WORKDIR: Path = Path("/app")
    # Spool area shared with the compute nodes (job scripts, token caches, logs)
    SPOOL_DIR: Path = Path("/nfs/form-runner")
    # Wrapper to submit as the mapped local user, e.g. "gosu local-user" (empty = none)
    SBATCH_USER_WRAPPER: str = "gosu local-user"
    SLURM_USER: str = "local-user"
    RUNNER_TIME_LIMIT: str = "00:30:00"

    # Environment handed to the runner job (consumed by jobbergate-cli inside the job)
    RUNNER_BASE_API_URL: str = "http://jobbergate-api:80"
    RUNNER_OIDC_DOMAIN: str = "keycloak.local:8080/realms/jobbergate-local"
    RUNNER_OIDC_CLIENT_ID: str = "cli"
    RUNNER_OIDC_USE_HTTPS: bool = False
    # Path to sbatch inside the compute nodes; enables on-site submission from the runner
    RUNNER_SBATCH_PATH: str = "/usr/bin/sbatch"
    RUNNER_DEFAULT_CLUSTER_NAME: str = "local-slurm"
    RUNNER_UV_CACHE_DIR: str = "/slurm-work-dir/.uv-cache"
    RUNNER_UV_PROJECT_ENVIRONMENT: str = "/slurm-work-dir/.uv-venvs/jobbergate-cli"

    MAX_ANSWER_CHARS: int = 10_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
