"""
Provide tool functions for working with Job Script data
"""

import json
import pathlib
from typing import Any, Dict, List, Optional, cast

from loguru import logger

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobScriptCreateRequestData, JobScriptResponse
from jobbergate_cli.subapps.applications.tools import execute_application, fetch_application_data, load_application_data


def validate_parameter_file(parameter_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate parameter file at the supplied path and returns the parsed dict.

    Confirms:
        parameter_path exists
        parameter_path is a valid json file
    """
    data = None
    with Abort.check_expressions(
        f"The parameter file at {parameter_path} was invalid",
        raise_kwargs=dict(
            subject="Invalid parameter file",
            log_message=f"Parameter file located at {parameter_path} failed validation",
        ),
    ) as checker:
        checker(
            parameter_path.exists(),
            f"Parameter file {parameter_path} does not exist",
        )

        try:
            data = json.loads(parameter_path.read_text())
            is_valid_json = True
        except Exception:
            is_valid_json = False
        checker(is_valid_json, f"The parameter file at {parameter_path} is not valid JSON")

    # Make static type checkers happy
    assert data is not None
    return data


def fetch_job_script_data(
    jg_ctx: JobbergateContext,
    id: int,
) -> JobScriptResponse:
    """
    Retrieve a job_script from the API by ``id``
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None

    return cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/{id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job script ({id}) from API",
            support=True,
            response_model_cls=JobScriptResponse,
        ),
    )


def create_job_script(
    jg_ctx: JobbergateContext,
    name: Optional[str] = None,
    application_id: Optional[int] = None,
    application_identifier: Optional[str] = None,
    description: Optional[str] = None,
    sbatch_params: Optional[List[str]] = None,
    param_file: Optional[pathlib.Path] = None,
    fast: bool = False,
) -> JobScriptResponse:
    """
    Create a new job script.

    :param str name: Name of the new job script.
    :param Optional[int] application_id: Id of the base application.
    :param Optional[str] application_identifier: Identifier of the base application.
    :param Optional[str] description: Description of the new job script.
    :param Optional[List[str]] sbatch_params: List of sbatch parameters.
    :param Optional[pathlib.Path] param_file: Path to a parameters file.
    :param bool fast: Whether to use default answers (when available) instead of asking the user.
    :param JobbergateContext jg_ctx: The Jobbergate context.
    :return JobScriptResponse: The new job script.
    """
    app_data = fetch_application_data(jg_ctx, id=application_id, identifier=application_identifier)
    (app_config, app_module) = load_application_data(app_data)

    request_data = JobScriptCreateRequestData(
        application_id=app_data.id,
        job_script_name=name if name else app_data.application_name,
        sbatch_params=sbatch_params,
        param_dict=app_config,
        job_script_description=description,
    )

    supplied_params = validate_parameter_file(param_file) if param_file else dict()
    execute_application(app_module, app_config, supplied_params, fast_mode=fast)

    if app_config.jobbergate_config.job_script_name is not None:
        request_data.job_script_name = app_config.jobbergate_config.job_script_name

    # Make static type checkers happy
    assert jg_ctx.client is not None

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            "/jobbergate/job-scripts",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job script",
            support=True,
            request_model=request_data,
            response_model_cls=JobScriptResponse,
        ),
    )

    return job_script_result


def save_job_script_files(
    job_script_data: JobScriptResponse,
    destination_path: pathlib.Path,
) -> List[pathlib.Path]:
    """
    Save the job script files from the API response to the output path.
    """
    logger.debug(f"Saving job script files to {destination_path.as_posix()}")
    saved_files: List[pathlib.Path] = []

    for filename, file_content in job_script_data.job_script_files.files.items():
        file_path = destination_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_content)
        saved_files.append(file_path)

    logger.debug(f"The following files were saved: {list(map(str, saved_files))}")
    return saved_files


def download_job_script_files(id: int, jg_ctx: JobbergateContext) -> List[pathlib.Path]:
    """
    Download the job script files from the API and save them to the current working directory.
    """
    result = fetch_job_script_data(jg_ctx, id)
    downloaded_files = save_job_script_files(
        job_script_data=result,
        destination_path=pathlib.Path.cwd(),
    )
    return downloaded_files
