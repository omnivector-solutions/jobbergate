"""
Provide tool functions for working with Job Submission data
"""

import copy
import json
import pathlib
import subprocess
import tempfile
from typing import Any, Dict, Optional, cast

from jobbergate_cli.config import settings
from jobbergate_cli.constants import JOBBERGATE_JOB_SUBMISSION_CONFIG
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobScriptResponse, JobSubmissionResponse
from jobbergate_cli.subapps.applications.tools import fetch_application_data
from jobbergate_cli.subapps.job_scripts.tools import fetch_job_script_data
from jobbergate_cli.text_tools import dedent


def load_default_config() -> Dict[str, Any]:
    """
    Load the default config for a job submission.
    """
    return copy.deepcopy(JOBBERGATE_JOB_SUBMISSION_CONFIG)


def run_job_script(
    job_script_data: JobScriptResponse,
    application_name: str,
    build_path: Optional[pathlib.Path] = None,
) -> int:
    """
    Submit a Job Script to slurm via ``sbatch``.

    :param: job_script_data: A JobScriptResponse including the script and its configuration
    :param: application_name: The name of the application to pass to ``sbatch``
    :param: build_path:       An optional directory where the job script templates and job script should be unpacked
    :returns: The ``slurm_job_id`` for the submitted job
    """
    Abort.require_condition(
        settings.SBATCH_PATH.exists(),
        dedent(
            f"""
            sbatch executable was not found at {settings.SBATCH_PATH}.
            Please confirm that sbatch is installed and the environment variable SBATCH_PATH directs to it.
            """
        ),
        raise_kwargs=dict(
            subject="Sbatch executable not found",
            support=True,
        ),
    )

    job_script_name = job_script_data.job_script_name
    unpacked_data = json.loads(job_script_data.job_script_data_as_string)

    if build_path is None:
        temp_build_dir = tempfile.TemporaryDirectory()
        build_path = pathlib.Path(temp_build_dir.name)
    else:
        Abort.require_condition(
            build_path.exists(),
            dedent(
                f"""
                The supplied build directory does not exist: {build_path}.
                """
            ),
            raise_kwargs=dict(
                subject="Build dir does not exist",
                support=True,
            ),
        )

    script_path = None
    for (filename, data) in unpacked_data.items():
        if filename == "application.sh":
            filename = f"{job_script_name}.job"
            script_path = build_path / filename

        file_path = build_path / filename
        file_path.write_text(data)

    Abort.require_condition(
        script_path is not None,
        dedent(
            f"""
            Could not find an executable script in retrieved job script data.
            It's likely that this job_script ({job_script_data.id}) is broken.
            """,
        ),
        raise_kwargs=dict(
            support=True,
            subject="Invalid job script",
            log_message="job_script {job_script_id} is missing `application.sh`. It cannot be submitted.",
        ),
    )

    # Make static type checkers happy
    assert settings.SBATCH_PATH is not None
    assert script_path is not None

    cmd = [settings.SBATCH_PATH, script_path, application_name]
    proc = subprocess.run(cmd, capture_output=True, text=True, input="sbatch output")

    Abort.require_condition(
        proc.returncode == 0,
        f"Failed to execute job submission with error: {proc.stderr}.",
        raise_kwargs=dict(
            subject="Job execution failed",
            support=True,
        ),
    )
    slurm_job_id = int(proc.stdout.split()[-1])
    return slurm_job_id


def create_job_submission(
    jg_ctx: JobbergateContext,
    job_script_id: int,
    name: str,
    description: Optional[str] = None,
) -> JobSubmissionResponse:
    """
    Creae a Job Submission from the given Job Script.

    :param: jg_ctx:        The JobbergateContext. Used to retrieve the client for requests
                           and the email of the submitting user
    :param: job_script_id: The ``id`` of the Job Script to submit to Slurm
    :param: name:          The name to attach to the Job Submission
    :param: description:   An optional description that may be added to the Job Submission
    :returns: The Job Submission data returned by the API after creating the new Job Submission
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None, "jg_ctx.client is uninitialized"
    assert jg_ctx.persona is not None, "jg_ctx.persona is uninitialized"

    job_script_data = fetch_job_script_data(jg_ctx, job_script_id)

    application_id = job_script_data.application_id
    application_data = fetch_application_data(jg_ctx, id=application_id)
    application_name = application_data.application_name

    slurm_job_id = run_job_script(job_script_data, application_name)
    owner_email = jg_ctx.persona.identity_data.user_email

    job_submission_data = dict(
        job_submission_name=name,
        job_submission_description=description,
        job_submission_owner_email=owner_email,
        job_script_id=job_script_id,
        slurm_job_id=slurm_job_id,
    )

    result = cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            "/job-submissions",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job submission",
            support=True,
            json=job_submission_data,
            response_model=JobSubmissionResponse,
        ),
    )
    return result


def fetch_job_submission_data(
    jg_ctx: JobbergateContext,
    job_submission_id: int,
) -> JobSubmissionResponse:
    """
    Retrieve a job submission from the API by ``id``
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    return cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            f"/job-submissions/{job_submission_id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job submission {job_submission_id} from API",
            support=True,
            response_model=JobSubmissionResponse,
        ),
    )
