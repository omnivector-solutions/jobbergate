"""
Thin subprocess wrappers around the Slurm client commands (sbatch, scontrol, scancel).

The API container is a submit host: it shares the cluster's munge key and slurm.conf,
so the regular CLI tools work directly. Commands are executed as ``SUBMIT_USER`` via
``gosu`` when the API runs as root (the composed PoC), since Slurm rejects root jobs.
"""

import os
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from jobbergate_cluster_api.config import settings


class SlurmError(RuntimeError):
    """Raised when a Slurm client command fails."""


def _as_submit_user(command: list[str]) -> list[str]:
    """Prefix the command with gosu when running as root and gosu is available."""
    if os.geteuid() == 0 and shutil.which("gosu"):
        return ["gosu", settings.SUBMIT_USER, *command]
    return command


def _run(command: list[str]) -> str:
    logger.debug("Running slurm command: {}", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SlurmError(f"{command[0]} failed (rc={result.returncode}): {result.stderr.strip()}")
    return result.stdout.strip()


def sbatch(script_path: Path) -> int:
    """Submit the session job script and return the slurm job id."""
    output = _run(_as_submit_user([str(settings.SBATCH_PATH), "--parsable", str(script_path)]))
    # --parsable prints "<job_id>[;<cluster>]"
    return int(output.split(";")[0])


def job_state(slurm_job_id: int) -> str | None:
    """
    Return the JobState reported by scontrol, or None when the job is no longer known
    (purged after MinJobAge).
    """
    try:
        output = _run([str(settings.SCONTROL_PATH), "show", "job", str(slurm_job_id), "-o"])
    except SlurmError as err:
        logger.debug("scontrol lookup failed for job {}: {}", slurm_job_id, err)
        return None
    for token in output.split():
        key, _, value = token.partition("=")
        if key == "JobState":
            return value
    return None


def scancel(slurm_job_id: int) -> None:
    """Cancel the session job. Missing jobs are tolerated."""
    try:
        _run(_as_submit_user([str(settings.SCANCEL_PATH), str(slurm_job_id)]))
    except SlurmError as err:
        logger.warning("scancel for job {} failed: {}", slurm_job_id, err)
