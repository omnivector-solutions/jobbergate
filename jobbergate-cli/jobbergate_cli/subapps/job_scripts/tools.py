"""
Provide tool functions for working with Job Script data
"""

import json
import pathlib
import re
import tempfile
from typing import Any, Dict, List, Optional, cast

from loguru import logger

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import (
    ApplicationResponse,
    JobbergateApplicationConfig,
    JobbergateConfig,
    JobbergateContext,
    JobScriptCreateRequest,
    JobScriptCreateRequestData,
    JobScriptResponse,
    RenderFromTemplateRequest,
)
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


def flatten_param_dict(param_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten an input dictionary to support the rendering process.

    See the example:

    >>> param_dict = {
    ...     "application_config": {"job_name": "rats", "partitions": [...]},
    ...     "jobbergate_config": {
    ...         "default_template": "test_job_script.sh",
    ...         "supporting_files": [...],
    ...         "supporting_files_output_name": {...},
    ...         "template_files": [...],
    ...         "job_script_name": None,
    ...         "output_directory": ".",
    ...         "partition": "debug",
    ...         "job_name": "rats",
    ...     },
    ... }
    >>> flat_param_dict = flatten_param_dict(param_dict)
    >>> print(flat_param_dict)
    {
        "job_name": "rats",
        "partitions": ["debug", "partition1"],
        "default_template": "test_job_script.sh",
        "supporting_files": ["test_job_script.sh"],
        "supporting_files_output_name": {"test_job_script.sh": [...]},
        "template_files": ["templates/test_job_script.sh"],
        "job_script_name": None,
        "output_directory": ".",
        "partition": "debug",
    }
    """
    param_dict_flat = {}
    for key, value in param_dict.items():
        if isinstance(value, dict):
            for nest_key, nest_value in value.items():
                param_dict_flat[nest_key] = nest_value
        else:
            param_dict_flat[key] = value
    return param_dict_flat


def remove_prefix(s: str) -> str:
    """Remove the prefix 'templates/' from a string"""
    return re.sub(r"^templates/", "", s)


def remove_prefix_suffix(s: str) -> str:
    """Remove the prefix 'templates/' and suffixes '.j2' and '.jinja2' from a string"""
    s = remove_prefix(s)
    s = re.sub(r"(.j2|.jinja2)$", "", s)
    return s


def get_template_output_name_mapping(config: JobbergateConfig) -> Dict[str, str]:
    """
    Get the mapping of template names to output names.

    This provides the mapping as expected by the API v4 from the configuration on CLI v3.
    """
    output_dir = config.output_directory

    if not config.default_template:
        raise Abort(
            "Default template was not specified",
            subject="Entry point is unspecified",
            log_message="Entry point file not specified",
        )

    output_name_mapping = {config.default_template: output_dir / remove_prefix_suffix(config.default_template)}

    if config.supporting_files:
        for template in config.supporting_files:
            output_name_mapping[template] = output_dir / remove_prefix_suffix(template)
    if config.supporting_files_output_name:
        for template, output_name_list in config.supporting_files_output_name.items():
            if len(output_name_list) != 1:
                raise Abort(
                    f"{template=} has {len(output_name_list)} output names, one and only one is required",
                    subject="Supporting file output name is unspecified",
                    log_message="Supporting file output name is unspecified",
                )
            output_name_mapping[template] = output_dir / output_name_list[0]

    return {remove_prefix(k): v.as_posix() for k, v in output_name_mapping.items()}


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
    # Make static type checkers happy
    assert jg_ctx.client is not None

    app_data = fetch_application_data(jg_ctx, id=application_id, identifier=application_identifier)

    if not app_data.workflow_files:
        raise Abort(
            f"Application {app_data.id} does not have a workflow file",
            subject="Workflow file not found",
            log_message="Application does not have a workflow file",
        )

    with tempfile.NamedTemporaryFile() as fp:
        tmp_file_path = pathlib.Path(fp.name)
        make_request(
            jg_ctx.client,
            app_data.workflow_files[0].path,
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve application module file from API",
            save_to_file=tmp_file_path,
        )

        application_source_code = tmp_file_path.read_text()

    (app_config, app_module) = load_application_data(app_data, application_source_code)

    supplied_params = validate_parameter_file(param_file) if param_file else dict()
    execute_application(app_module, app_config, supplied_params, fast_mode=fast)
    update_template_files_information(app_data, app_config)

    param_dict_flat = flatten_param_dict(app_config.dict())

    request_data = JobScriptCreateRequestData(
        create_request=JobScriptCreateRequest(
            name=name if name else app_data.name,
            description=description,
        ),
        render_request=RenderFromTemplateRequest(
            template_output_name_mapping=get_template_output_name_mapping(app_config.jobbergate_config),
            sbatch_params=sbatch_params,
            param_dict={"data": param_dict_flat},
        ),
    )

    if app_config.jobbergate_config.job_script_name is not None:
        request_data.create_request.name = app_config.jobbergate_config.job_script_name

    # Make static type checkers happy
    assert jg_ctx.client is not None

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/render-from-template/{app_data.id}",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job script",
            support=True,
            request_model=request_data,
            response_model_cls=JobScriptResponse,
        ),
    )

    return job_script_result


def update_template_files_information(app_data: ApplicationResponse, app_config: JobbergateApplicationConfig):
    """Update the information about the template files if not already present in the configuration."""
    if not app_config.jobbergate_config.default_template:
        list_of_entrypoints = [i.filename for i in app_data.template_files if i.file_type.upper() == "ENTRYPOINT"]
        if len(list_of_entrypoints) != 1:
            raise Abort(
                f"Application {app_data.id} does not have one entry point, found {len(list_of_entrypoints)}",
                subject="Entry point is unspecified",
                log_message="Entry point file not specified",
            )
        app_config.jobbergate_config.default_template = list_of_entrypoints[0]

    if not app_config.jobbergate_config.supporting_files:
        list_of_supporting_files = [i.filename for i in app_data.template_files if i.file_type.upper() == "SUPPORT"]
        if list_of_supporting_files:
            app_config.jobbergate_config.supporting_files = list_of_supporting_files


def save_job_script_files(
    jg_ctx: JobbergateContext,
    job_script_data: JobScriptResponse,
    destination_path: pathlib.Path,
) -> List[pathlib.Path]:
    """
    Save the job script files from the API response to the output path.
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None

    logger.debug(f"Saving job script files to {destination_path.as_posix()}")
    saved_files: List[pathlib.Path] = []

    for metadata in job_script_data.files:
        filename = metadata.filename
        file_path = destination_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        make_request(
            jg_ctx.client,
            metadata.path,
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job script file {filename} from API",
            save_to_file=file_path,
        )
        saved_files.append(file_path)

    logger.debug(f"The following files were saved: {list(map(str, saved_files))}")
    return saved_files


def download_job_script_files(id: int, jg_ctx: JobbergateContext) -> List[pathlib.Path]:
    """
    Download the job script files from the API and save them to the current working directory.
    """
    result = fetch_job_script_data(jg_ctx, id)
    downloaded_files = save_job_script_files(
        jg_ctx,
        job_script_data=result,
        destination_path=pathlib.Path.cwd(),
    )
    return downloaded_files
