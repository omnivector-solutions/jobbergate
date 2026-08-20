"""
Cluster-side runner for the web question flow (see the ``create-web`` command).

This module executes inside the Slurm job launched by the Form Runner service. It fetches the
session context from the service's internal bridge, seeds the token cache with the session
owner's access token so the regular :class:`~jobbergate_cli.context.JobbergateContext`
authenticates as that user, and then reuses the standard ``jobbergate job-scripts create``
flow end to end (rendering through the API and, when requested, submitting right away in
on-site mode) — with the interactive prompts replaced by the web bridge.
"""

import os
import pathlib
from typing import Any, Dict

from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.context import JobbergateContext, active_context
from jobbergate_cli.subapps.applications.remote_prompt import BridgePrompter
from jobbergate_cli.subapps.applications.tools import active_prompt_backend
from jobbergate_core.auth.token import Token, TokenType


def run_web_session(*, bridge_url: str, session_id: str, session_secret: str) -> None:
    """
    Execute one Form Runner session: gather answers via the bridge and create the job script.
    """
    bridge = BridgePrompter(bridge_url=bridge_url, session_id=session_id, session_secret=session_secret)
    session = bridge.fetch_context()
    logger.info("Starting web session {} for application {}", session_id, session["application_id_or_identifier"])

    # Seed the token cache so the standard context machinery (client auth, identity data)
    # acts as the session owner without triggering any interactive login. The refresh
    # token (when forwarded) lets interviews outlive the access-token TTL.
    Token(
        cache_directory=settings.JOBBERGATE_USER_TOKEN_DIR,
        label=TokenType.ACCESS.value,
        content=session["access_token"],
    ).save_to_cache()
    if session.get("refresh_token"):
        Token(
            cache_directory=settings.JOBBERGATE_USER_TOKEN_DIR,
            label=TokenType.REFRESH.value,
            content=session["refresh_token"],
        ).save_to_cache()

    # Imported here to avoid a circular import (app.py exposes the command wrapping this module)
    from jobbergate_cli.subapps.job_scripts.app import create

    submit = bool(session.get("submit", False))
    # Without an explicit choice, land the job files in the session's spool work dir
    # instead of the runner's cwd (which is the shared workspace checkout)
    execution_directory = session.get("execution_directory") or os.environ.get("FORM_RUNNER_EXECUTION_DIR")
    try:
        with active_context(JobbergateContext()), active_prompt_backend(bridge):
            job_script, job_submission = create(
                id_or_identifier=str(session["application_id_or_identifier"]),
                name=session.get("name"),
                fast=bool(session.get("fast", False)),
                param_dict=session.get("supplied_params") or None,
                sbatch_params=session.get("sbatch_params") or None,
                submit=submit,
                download=False,
                # `create` forbids cluster/directory options outside submit mode
                cluster_name=session.get("cluster_name") if submit else None,
                execution_directory=pathlib.Path(execution_directory) if submit and execution_directory else None,
            )
        result: Dict[str, Any] = {
            "job_script_id": job_script.job_script_id,
            "job_script_name": job_script.name,
        }
        if job_submission is not None:
            result["job_submission_id"] = job_submission.job_submission_id
            result["slurm_job_id"] = job_submission.slurm_job_id
            status = getattr(job_submission, "status", None)
            if status is not None:
                result["job_submission_status"] = str(status)
        bridge.report_done(result)
        logger.info("Web session {} completed: {}", session_id, result)
    except Exception as err:
        logger.exception("Web session {} failed", session_id)
        bridge.report_failed(f"{type(err).__name__}: {err}")
        raise
