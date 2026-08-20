"""
Launch runner jobs for Form Runner sessions.

In ``slurm`` mode (the real deal) the session runs through **srun** on a dedicated shared
partition: the service writes the runner script plus the session context into a per-session
spool directory on the shared filesystem, chowns it to the mapped local user, and starts
``srun`` as that user. srun starts the step immediately (the partition oversubscribes, so
there is no queue wait) and the service holds the process handle — no job-status polling:
the runner's exit is observed directly, and cancellation is just terminating the process.
In ``subprocess`` mode the same runner command executes locally — useful for development.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import threading
from pathlib import Path

from loguru import logger

from jobbergate_form_runner.config import settings
from jobbergate_form_runner.sessions import TERMINAL_STATUSES, Session

_processes: dict[str, subprocess.Popen] = {}


def _runner_command(session: Session) -> str:
    return (
        "uv run --frozen --no-dev --package jobbergate-cli "
        f"jobbergate job-scripts create-web-runner --session-id {session.id} --bridge-url {settings.BRIDGE_URL}"
    )


def _runner_environment(session: Session, cache_dir: Path) -> dict[str, str]:
    return {
        "JOBBERGATE_FORM_RUNNER_SECRET": session.secret,
        "BASE_API_URL": settings.RUNNER_BASE_API_URL,
        "OIDC_DOMAIN": settings.RUNNER_OIDC_DOMAIN,
        "OIDC_CLIENT_ID": settings.RUNNER_OIDC_CLIENT_ID,
        "OIDC_USE_HTTPS": str(settings.RUNNER_OIDC_USE_HTTPS).lower(),
        "JOBBERGATE_CACHE_DIR": str(cache_dir),
        # On-site mode: the runner submits with the local sbatch right after rendering
        "SBATCH_PATH": settings.RUNNER_SBATCH_PATH,
        "DEFAULT_CLUSTER_NAME": settings.RUNNER_DEFAULT_CLUSTER_NAME,
        "UV_CACHE_DIR": settings.RUNNER_UV_CACHE_DIR,
        "UV_PROJECT_ENVIRONMENT": settings.RUNNER_UV_PROJECT_ENVIRONMENT,
        # Default landing zone for downloaded/submitted job files when the user
        # did not pick an execution directory
        "FORM_RUNNER_EXECUTION_DIR": str(cache_dir.parent / "work"),
    }


def _watch(session: Session, process: subprocess.Popen, mark_failed) -> None:
    """Watch the runner process; report an unexplained exit as a session failure."""
    returncode = process.wait()
    _processes.pop(session.id, None)
    logger.info("Runner process for session {} exited with code {}", session.id, returncode)
    if session.status not in TERMINAL_STATUSES:
        mark_failed(f"The runner exited unexpectedly (code {returncode}). Check {settings.SPOOL_DIR / session.id}.")


def launch(session: Session, mark_failed) -> None:
    """Start the runner for a session; raises on startup failure.

    ``mark_failed`` is a thread-safe callback used when the runner dies without reporting.
    """
    spool = settings.SPOOL_DIR / session.id
    cache_dir = spool / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    environment = _runner_environment(session, cache_dir)

    exports = "\n".join(f'export {key}="{value}"' for key, value in environment.items())
    script = spool / "runner.sh"
    script.write_text(
        "#!/bin/bash\n"
        f"{exports}\n"
        f"cd {settings.RUNNER_WORKDIR}\n"
        f"exec {_runner_command(session)}\n"
    )
    script.chmod(0o700)

    if settings.RUNNER_MODE == "subprocess":
        log_file = open(spool / "runner.log", "wb")
        process = subprocess.Popen(["bash", str(script)], cwd=settings.RUNNER_WORKDIR, stdout=log_file, stderr=log_file)
    else:
        # The runner (and therefore the script and spool) belongs to the mapped local user
        if shutil.which("chown"):
            subprocess.run(["chown", "-R", settings.SLURM_USER, str(spool)], check=False)
        wrapper = shlex.split(settings.SBATCH_USER_WRAPPER) if settings.SBATCH_USER_WRAPPER else []
        command = [
            *wrapper,
            "srun",
            f"--job-name=jg-web-{session.id}",
            f"--partition={settings.RUNNER_PARTITION}",
            "--ntasks=1",
            "--cpus-per-task=1",
            "--mem=100M",
            f"--time={settings.RUNNER_TIME_LIMIT}",
            f"--output={spool}/runner.log",
            "bash",
            str(script),
        ]
        logger.info("Starting runner for session {}: {}", session.id, " ".join(command))
        process = subprocess.Popen(command, cwd=spool, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    _processes[session.id] = process
    threading.Thread(target=_watch, args=(session, process, mark_failed), daemon=True).start()
    session.set_status("starting")


def cancel(session: Session) -> None:
    """Cancel a session's runner (best effort): terminating srun cancels the slurm step."""
    process = _processes.pop(session.id, None)
    if process is not None and process.poll() is None:
        process.terminate()
