import copy
import json
import pathlib
import subprocess
import tempfile
from typing import Any, Dict, Optional, cast

import snick

from jobbergate_cli.config import settings
from jobbergate_cli.constants import JOBBERGATE_JOB_SUBMISSION_CONFIG
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.subapps.applications.tools import fetch_application_data
from jobbergate_cli.subapps.job_scripts.tools import fetch_job_script_data


def load_default_config() -> Dict[str, Any]:
    """
    Load the default config for a job submission.
    """
    return copy.deepcopy(JOBBERGATE_JOB_SUBMISSION_CONFIG)


def run_job_script(
    job_script_data: Dict[str, Any],
    application_name: str,
    build_path: Optional[pathlib.Path] = None,
) -> int:
    """
    Execute Job Submission.
    """
    Abort.require_condition(
        settings.SBATCH_PATH.exists(),
        snick.dedent(
            f"""
            sbatch executable was not found at {settings.SBATCH_PATH}.
            Please confirm that sbatch is installed and the environment variable SBATCH_PATH directs to it.
            """
        ),
        raise_kwargs=dict(
            subject="SBATCH EXECUTABLE NOT FOUND",
            support=True,
        ),
    )

    job_script_name = job_script_data["job_script_name"]
    unpacked_data = json.loads(job_script_data["job_script_data_as_string"])

    if build_path is None:
        temp_build_dir = tempfile.TemporaryDirectory()
        build_path = pathlib.Path(temp_build_dir.name)
    else:
        Abort.require_condition(
            build_path.exists(),
            snick.dedent(
                f"""
                The supplied build directory does not exist: {build_path}.
                """
            ),
            raise_kwargs=dict(
                subject="BUILD DIR DOES NOT EXIST",
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
        snick.dedent(
            f"""
            Could not find an executable script in retrieved job script data.
            It's likely that this job_script ({job_script_data["id"]}) is broken.
            """,
        ),
        raise_kwargs=dict(
            support=True,
            subject="INVALID JOB SCRIPT",
            log_message="job_script {job_script_id} is missing `application.sh`. It cannot be submitted.",
        ),
    )

    cmd = [settings.SBATCH_PATH, script_path, application_name]
    proc = subprocess.run(cmd, capture_output=True, text=True, input="sbatch output")

    Abort.require_condition(
        proc.returncode == 0,
        f"Failed to execute job submission with error: {proc.stderr}.",
        raise_kwargs=dict(
            subject="JOB EXECUTION FAILED",
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
) -> Dict[Any, str]:
    """
    Upload an application given an application path and the application id.
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None, "jg_ctx.client is uninitialized"
    assert jg_ctx.persona is not None, "jg_ctx.persona is uninitialized"

    job_script_data = fetch_job_script_data(jg_ctx, job_script_id)

    application_id = job_script_data["application_id"]
    application_data = fetch_application_data(jg_ctx, id=application_id)
    application_name = application_data["application_name"]

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
        Dict[str, Any],
        make_request(
            jg_ctx.client,
            f"/job-submissions",
            "POST",
            expected_status=201,
            abort_message=f"Couldn't create job submission",
            support=True,
            json=job_submission_data,
        ),
    )
    return result


def fetch_job_submission_data(
    jg_ctx: JobbergateContext,
    job_submission_id: int,
) -> Dict[str, Any]:
    """
    Retrieve a job submission from the API by ``id``
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    return cast(
        Dict[str, Any],
        make_request(
            jg_ctx.client,
            f"/job-submissions/{job_submission_id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job submission {job_submission_id} from API",
            support=True,
        ),
    )
