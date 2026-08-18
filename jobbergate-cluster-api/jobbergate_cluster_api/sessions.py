"""
Session management: create the per-session workdir, seed the token cache, submit the
session job wrapping ``ttyd`` + ``jobbergate job-scripts create``, and track lifecycle.

Sessions are persisted as ``meta.json`` files inside their own directory under
``SESSIONS_DIR`` so the API remains stateless across restarts — Slurm owns the process.
"""

import json
import secrets
import shutil
import string
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from jobbergate_cluster_api import slurm
from jobbergate_cluster_api.config import settings
from jobbergate_cluster_api.schemas import SessionStatus

# Slurm job states mapped onto session statuses. RUNNING is refined by the presence
# of the endpoint file (ttyd only counts as up once the job wrote host:port).
_STATE_MAP = {
    "PENDING": SessionStatus.PENDING,
    "CONFIGURING": SessionStatus.PENDING,
    "RUNNING": SessionStatus.RUNNING,
    "COMPLETING": SessionStatus.RUNNING,
    "COMPLETED": SessionStatus.FINISHED,
    "FAILED": SessionStatus.FAILED,
    "TIMEOUT": SessionStatus.FAILED,
    "NODE_FAIL": SessionStatus.FAILED,
    "OUT_OF_MEMORY": SessionStatus.FAILED,
    "PREEMPTED": SessionStatus.FAILED,
    "CANCELLED": SessionStatus.CANCELLED,
}


class _JobTemplate(string.Template):
    """string.Template with a delimiter that does not collide with bash's ``$``."""

    delimiter = "%%"


SESSION_JOB_TEMPLATE = _JobTemplate(
    """#!/bin/bash
#SBATCH --job-name=jg-session-%%session_id
#SBATCH --partition=%%partition
#SBATCH --output=%%session_dir/session.log
set -uo pipefail

# The CLI reads its credentials from this cache directory (seeded by the cluster API),
# and SBATCH_PATH switches it to on-site submission mode.
export JOBBERGATE_CACHE_DIR=%%session_dir/cache
export SBATCH_PATH=%%sbatch_path
export BASE_API_URL=%%base_api_url
export OIDC_DOMAIN=%%oidc_domain
export OIDC_CLIENT_ID=%%oidc_client_id
export OIDC_USE_HTTPS=%%oidc_use_https
export DEFAULT_CLUSTER_NAME=%%cluster_name
export UV_CACHE_DIR=%%uv_cache_dir
export UV_PROJECT_ENVIRONMENT=%%uv_env_dir

PORT=$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1])')
echo "$(hostname):${PORT}" > %%session_dir/endpoint

cd %%session_dir/work

ttyd --once --writable --port "${PORT}" --base-path %%base_path \\
    uv run --project %%app_dir --package jobbergate-cli \\
    jobbergate job-scripts create %%selector \\
    --submit --cluster-name %%cluster_name --execution-directory %%session_dir/work

echo "$?" > %%session_dir/exit_code
"""
)


@dataclass
class Session:
    """In-memory view of a session, backed by its ``meta.json``."""

    session_id: str
    application_selector: str
    slurm_job_id: int
    otp: str
    owner_email: str | None
    created_at: str

    @property
    def session_dir(self) -> Path:
        return settings.SESSIONS_DIR / self.session_id


class SessionNotFound(Exception):
    """Raised when a session id does not resolve to a session directory."""


def _seed_token_cache(cache_dir: Path, access_token: str, refresh_token: str | None) -> None:
    """
    Write the forwarded tokens where ``JobbergateAuthHandler`` expects them:
    ``<JOBBERGATE_CACHE_DIR>/token/<label>.token`` with restrictive permissions.
    """
    token_dir = cache_dir / "token"
    token_dir.mkdir(parents=True, exist_ok=True)
    access_path = token_dir / "access.token"
    access_path.write_text(access_token.strip())
    access_path.chmod(0o600)
    if refresh_token:
        refresh_path = token_dir / "refresh.token"
        refresh_path.write_text(refresh_token.strip())
        refresh_path.chmod(0o600)


def _chown_for_submit_user(path: Path) -> None:
    """Hand the session tree to the submit user; best-effort outside the container."""
    try:
        for item in [path, *path.rglob("*")]:
            shutil.chown(item, user=settings.SUBMIT_USER, group=settings.SUBMIT_USER)
    except (PermissionError, LookupError, KeyError) as err:
        logger.warning("Could not chown {} to {}: {}", path, settings.SUBMIT_USER, err)


def render_session_script(session_id: str, session_dir: Path, selector: str) -> str:
    """Render the session job script for the given application selector."""
    return SESSION_JOB_TEMPLATE.substitute(
        session_id=session_id,
        partition=settings.SESSIONS_PARTITION,
        session_dir=str(session_dir),
        sbatch_path=str(settings.SBATCH_PATH),
        base_api_url=settings.CLI_BASE_API_URL,
        oidc_domain=settings.CLI_OIDC_DOMAIN,
        oidc_client_id=settings.CLI_OIDC_CLIENT_ID,
        oidc_use_https=str(settings.CLI_OIDC_USE_HTTPS).lower(),
        cluster_name=settings.CLUSTER_NAME,
        uv_cache_dir=str(settings.UV_CACHE_DIR),
        uv_env_dir=str(settings.UV_ENV_DIR),
        app_dir=str(settings.APP_DIR),
        base_path=f"{settings.BASE_PATH}/{session_id}/terminal",
        selector=selector,
    )


def create_session(
    selector: str,
    access_token: str,
    refresh_token: str | None = None,
    owner_email: str | None = None,
) -> Session:
    """
    Create the session directory, seed the token cache, and sbatch the session job.
    """
    session_id = uuid.uuid4().hex[:12]
    session_dir = settings.SESSIONS_DIR / session_id
    (session_dir / "work").mkdir(parents=True)
    _seed_token_cache(session_dir / "cache", access_token, refresh_token)

    script_path = session_dir / "session-job.sh"
    script_path.write_text(render_session_script(session_id, session_dir, selector))
    script_path.chmod(0o700)
    _chown_for_submit_user(session_dir)

    slurm_job_id = slurm.sbatch(script_path)

    session = Session(
        session_id=session_id,
        application_selector=selector,
        slurm_job_id=slurm_job_id,
        otp=secrets.token_urlsafe(32),
        owner_email=owner_email,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    meta_path = session_dir / "meta.json"
    meta_path.write_text(json.dumps(asdict(session), indent=2))
    meta_path.chmod(0o600)
    logger.info("Session {} created (slurm job {}) for application {}", session_id, slurm_job_id, selector)
    return session


def load_session(session_id: str) -> Session:
    """Load a session from its ``meta.json``; raise ``SessionNotFound`` otherwise."""
    meta_path = settings.SESSIONS_DIR / session_id / "meta.json"
    if not meta_path.is_file():
        raise SessionNotFound(session_id)
    return Session(**json.loads(meta_path.read_text()))


def session_status(session: Session) -> tuple[SessionStatus, int | None]:
    """
    Derive the session status from the exit-code file, slurm state, and endpoint file.

    Returns the status along with the CLI exit code when the session already ended.
    """
    exit_code_path = session.session_dir / "exit_code"
    if exit_code_path.is_file():
        exit_code = int(exit_code_path.read_text().strip() or "1")
        return (SessionStatus.FINISHED if exit_code == 0 else SessionStatus.FAILED), exit_code

    state = slurm.job_state(session.slurm_job_id)
    if state is None:
        # Job purged from slurm's memory and no exit code recorded
        return SessionStatus.UNKNOWN, None
    status = _STATE_MAP.get(state.split()[0].rstrip("+"), SessionStatus.UNKNOWN)
    if status is SessionStatus.RUNNING and not (session.session_dir / "endpoint").is_file():
        # The job started but ttyd has not published its endpoint yet
        status = SessionStatus.PENDING
    return status, None


def session_endpoint(session: Session) -> str | None:
    """Return ``host:port`` of the session's ttyd instance, when published."""
    endpoint_path = session.session_dir / "endpoint"
    if not endpoint_path.is_file():
        return None
    return endpoint_path.read_text().strip() or None


def cancel_session(session: Session) -> None:
    """Cancel the session job and shred the seeded credentials."""
    slurm.scancel(session.slurm_job_id)
    shred_credentials(session)


def shred_credentials(session: Session) -> None:
    """Remove the seeded token cache once the session is over."""
    token_dir = session.session_dir / "cache" / "token"
    if token_dir.is_dir():
        shutil.rmtree(token_dir, ignore_errors=True)
        logger.info("Shredded token cache for session {}", session.session_id)
