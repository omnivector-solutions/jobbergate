"""
Provide tool functions for working with Job Script data
"""

import json
import pathlib
import re
import tempfile
from concurrent import futures
from functools import partial
from typing import Any, Callable, Dict, List, Optional, cast

from jinja2.sandbox import SandboxedEnvironment
from jinja2.exceptions import SecurityError, UndefinedError
from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.constants import FileType
from jobbergate_cli.exceptions import Abort, JobbergateCliError
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import (
    JobbergateConfig,
    ContextProtocol,
    JobScriptCreateRequest,
    JobScriptFile,
    JobScriptRenderRequestData,
    JobScriptResponse,
    RenderFromTemplateRequest,
)
from jobbergate_cli.subapps.applications.tools import (
    ApplicationRuntime,
    fetch_application_data,
    fetch_application_data_locally,
)


def validate_parameter_file(parameter_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate parameter file at the supplied path and returns the parsed dict.

    Args:
        parameter_path: Path to the parameter file.

    Raises:
        Abort: If file does not exist or is not valid JSON.

    Returns:
        Parsed dictionary from the parameter file.
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
    jg_ctx: ContextProtocol,
    id: int,
) -> JobScriptResponse:
    """
    Retrieve a job_script from the API by ``id``
    """
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


def remove_prefix(s: str) -> str:
    """Remove the prefix 'templates/' from a string"""
    return re.sub(r"^templates/", "", s)


def remove_prefix_suffix(s: str) -> str:
    """Remove the prefix 'templates/' and suffixes '.j2' and '.jinja2' from a string"""
    s = remove_prefix(s)
    s = re.sub(r"(.j2|.jinja2)$", "", s)
    return s


def get_template_output_name_mapping(config: JobbergateConfig, job_name: str) -> Dict[str, str]:
    """
    Get the mapping of template names to output names.

    This provides the mapping as expected by the API v4 from the configuration on CLI v3.
    """
    output_dir = pathlib.Path(".")

    if not config.default_template:
        raise Abort(
            "Default template was not specified",
            subject="Entry point is unspecified",
            log_message="Entry point file not specified",
        )

    if settings.JOBBERGATE_LEGACY_NAME_CONVENTION:
        job_script_file_name = f"{job_name}.job"
    else:
        job_script_file_name = remove_prefix_suffix(config.default_template)

    output_name_mapping = {config.default_template: output_dir / job_script_file_name}

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


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    logger.debug("Preparing to inject sbatch params into job script")

    if not sbatch_params:
        logger.warning("Sbatch param list is empty")
        return job_script_data_as_string

    # Find the first non-blank, non-comment line
    match = re.search(r"^[^#\n]", job_script_data_as_string, re.MULTILINE)
    if match:
        insert_index = match.start()
    else:
        # If no such line is found, append at the end
        insert_index = len(job_script_data_as_string)

    inner_string = "# Sbatch params injected at rendering time\n"
    for parameter in sbatch_params:
        inner_string += f"#SBATCH {parameter}\n"
    else:
        inner_string += "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:insert_index] + inner_string + job_script_data_as_string[insert_index:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


def render_template(
    template_path: pathlib.Path,
    parameters: Dict[str, Any],
) -> str:
    """
    Render a template file and save it to the output directory.

    Args:
        template_path: The path to the template file.
        parameters: The parameters to use for rendering the template.

    Returns:
        The rendered template as a string.
    """

    logger.debug("Rendering template file: {} with parameters={}", template_path, parameters)

    Abort.require_condition(template_path.is_file(), f"Template file {template_path} does not exist or is not a file")

    with open(template_path, "r") as f:
        file_content = f.read()

    with Abort.handle_errors(
        f"Unable to process jinja template filename={template_path}",
        raise_kwargs=dict(
            subject="Unable to process jinja template",
            log_message=f"Unable to process jinja template filename={template_path}",
        ),
    ):
        sandbox_env = SandboxedEnvironment()
        template = sandbox_env.from_string(file_content)

    render_contexts = [parameters, {"data": parameters}]

    for context in render_contexts:
        try:
            return template.render(**context)
        except SecurityError:
            raise Abort(
                f"Security errors raised when rendering filename={template_path}",
                subject="Unable to render jinja template",
                log_message=f"Security error rendering filename={template_path}",
            )
        except UndefinedError as e:
            logger.debug(
                "Unable to render filename={} with context={} -- Error: {}",
                template_path,
                context,
                str(e),
            )

    raise Abort(
        f"Unable to render filename={template}",
        subject="Unable to render jinja template",
        log_message=f"Unable to render filename={template} with context={context}",
    )


def render_job_script_locally(
    jg_ctx: ContextProtocol,
    job_script_name: str,
    application_path: pathlib.Path,
    output_path: pathlib.Path,
    sbatch_params: Optional[List[str]] = None,
    param_file: Optional[pathlib.Path] = None,
    fast: bool = False,
):
    """
    Render a new job script from an application in a local directory.

    Args:
        jg_ctx: The Jobbergate context.
        job_script_name: Name of the new job script.
        application_path: Path to the base application.
        output_path: Path to the output the rendered job script.
        sbatch_params: List of sbatch parameters.
        param_file: Path to a parameters file.
        fast: Whether to use default answers (when available) instead of asking the user.
    """
    app_data = fetch_application_data_locally(application_path)

    if not app_data.workflow_files:
        raise Abort(
            "Application does not have a workflow file",
            subject="Workflow file not found",
            log_message="Application does not have a workflow file",
        )

    application_source_code = app_data.workflow_files[0].path.read_text()

    application_runtime = ApplicationRuntime(
        app_data,
        application_source_code,
        fast_mode=fast,
        sdk=jg_ctx.sdk,
        supplied_params=validate_parameter_file(param_file) if param_file else dict(),
    )
    application_runtime.execute_application()
    param_dict_flat = application_runtime.as_flatten_param_dict()

    if param_dict_flat.get("job_script_name"):
        # Possibly overwrite script name if set at runtime by the application
        job_script_name = param_dict_flat["job_script_name"]
        logger.debug("Job script name was set by the application at runtime: {}", job_script_name)

    template_name_mapping = get_template_output_name_mapping(
        application_runtime.app_config.jobbergate_config, job_script_name
    )

    mapped_template_files = {
        new_filename: file
        for file in app_data.template_files
        if (new_filename := template_name_mapping.get(file.filename, None))
    }

    for new_filename, template_file in mapped_template_files.items():
        file_content = render_template(template_file.path, param_dict_flat)

        if template_file.file_type == FileType.ENTRYPOINT and sbatch_params:
            file_content = inject_sbatch_params(file_content, sbatch_params)

        with open(output_path / new_filename, "w") as f:
            f.write(file_content)

        logger.debug("Rendered template file {} to: {}", template_file.filename, new_filename)


def render_job_script(
    jg_ctx: ContextProtocol,
    id_or_identifier: int | str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sbatch_params: Optional[List[str]] = None,
    param_file: Optional[pathlib.Path] = None,
    fast: bool = False,
) -> JobScriptResponse:
    """
    Render a new job script from an application.

    Args:
        jg_ctx: The Jobbergate context.
        name: Name of the new job script.
        application_id: Id of the base application.
        application_identifier: Identifier of the base application.
        description: Description of the new job script.
        sbatch_params: List of sbatch parameters.
        param_file: Path to a parameters file.
        fast: Whether to use default answers (when available) instead of asking the user.

    Returns:
        The new job script.
    """
    app_data = fetch_application_data(jg_ctx, id_or_identifier)

    if not app_data.workflow_files:
        raise Abort(
            f"Application {app_data.application_id} does not have a workflow file",
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

    application_runtime = ApplicationRuntime(
        app_data,
        application_source_code,
        fast_mode=fast,
        sdk=jg_ctx.sdk,
        supplied_params=validate_parameter_file(param_file) if param_file else dict(),
    )
    application_runtime.execute_application()
    param_dict_flat = application_runtime.as_flatten_param_dict()

    job_script_name = name if name else app_data.name

    if param_dict_flat.get("job_script_name"):
        # Possibly overwrite script name if set at runtime by the application
        job_script_name = param_dict_flat["job_script_name"]
        logger.debug("Job script name was set by the application at runtime: {}", job_script_name)

    request_data = JobScriptRenderRequestData(
        create_request=JobScriptCreateRequest(
            name=job_script_name,
            description=description,
        ),
        render_request=RenderFromTemplateRequest(
            template_output_name_mapping=get_template_output_name_mapping(
                application_runtime.app_config.jobbergate_config, job_script_name
            ),
            sbatch_params=sbatch_params,
            param_dict={"data": param_dict_flat},
        ),
    )

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/render-from-template/{app_data.application_id}",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job script",
            support=True,
            request_model=request_data,
            response_model_cls=JobScriptResponse,
        ),
    )

    return job_script_result


def upload_job_script_files(
    jg_ctx: ContextProtocol,
    job_script_id: int,
    job_script_path: pathlib.Path,
    supporting_file_paths: list[pathlib.Path] | None = None,
):
    """
    Upload a job-script and its supporting files given their paths and the job-script id.

    Args:
        jg_ctx: The ``JobbergateContext`` needed to access the Httpx client with which to make API calls
        job_script_path: The path to the job-script file to upload
        supporting_file_paths: The paths to any supporting files to upload with the job-scritpt
        job_script_id: The id of the job-script for which to upload  data
    """

    client = JobbergateCliError.enforce_defined(jg_ctx.client)

    Abort.require_condition(job_script_path.exists(), f"Job Script file {job_script_path} does not exist")
    Abort.require_condition(job_script_path.is_file(), f"Job Script file {job_script_path} is not a file")

    if supporting_file_paths is None:
        supporting_file_paths = []
    for sfp in supporting_file_paths:
        Abort.require_condition(sfp.exists(), f"Supporting file {job_script_path} does not exist")
        Abort.require_condition(sfp.is_file(), f"Supporting file {job_script_path} is not a file")

    with open(job_script_path, "rb") as job_script_file:
        response_code = cast(
            int,
            make_request(
                client,
                f"/jobbergate/job-scripts/{job_script_id}/upload/{FileType.ENTRYPOINT.value}",
                "PUT",
                expect_response=False,
                abort_message="Request to upload job-script files was not accepted by the API",
                support=True,
                files={"upload_file": (job_script_path.name, job_script_file, "text/plain")},
            ),
        )
        Abort.require_condition(response_code == 200, f"Job Script file {job_script_path} failed to upload")

    with JobbergateCliError.check_expressions("Some supporting files failed to upload") as check:
        for supporting_file_path in supporting_file_paths:
            with open(supporting_file_path, "rb") as supporting_file:
                response_code = cast(
                    int,
                    make_request(
                        client,
                        f"/jobbergate/job-scripts/{job_script_id}/upload/{FileType.SUPPORT.value}",
                        "PUT",
                        expect_response=False,
                        abort_message="Request to upload job-script supporting file was not accepted by the API",
                        support=True,
                        files={"upload_file": (supporting_file_path.name, supporting_file, "text/plain")},
                    ),
                )
                check(
                    response_code == 200,
                    f"Supporting file {supporting_file_path} was not accepted by the API for download",
                )


def save_job_script_file(
    jg_ctx: ContextProtocol, destination_path: pathlib.Path, job_script_file: JobScriptFile
) -> pathlib.Path:
    """
    Save a job script file from the API response to the destination path.
    """
    filename = job_script_file.filename
    file_path = destination_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    make_request(
        jg_ctx.client,
        job_script_file.path,
        "GET",
        expected_status=200,
        abort_message=f"Couldn't retrieve job script file {filename} from API",
        save_to_file=file_path,
    )

    logger.debug("Downloaded {}", file_path.as_posix())
    return file_path


def download_job_script_files(id: int, jg_ctx: ContextProtocol, destination_path: pathlib.Path) -> List[JobScriptFile]:
    """
    Download all job script files from the API and save them to the destination path.
    """

    result = fetch_job_script_data(jg_ctx, id)

    with futures.ThreadPoolExecutor() as executor:
        executor.map(partial(save_job_script_file, jg_ctx, destination_path), result.files)

    return result.files


def question_helper(question_func: Callable, text: str, default: Any, fast: bool, actual_value: Optional[Any]):
    """
    Helper function for asking questions to the user.

    Args:
        question_func: The function to use to ask the question
        text: The text of the question to ask
        default: The default value to use if the user does not provide one
        fast: Whether to use default answers (when available) instead of asking the user
        actual_value: The actual value provided by the user, if any

    Returns:
        `actual_value` or `default` or the value provided by the user

    Notes:
        The `actual_value` has the most priority and will be returned if it is not None.
        After evaluating the `actual_value`, the fast mode will determine if the default value will be used.
        Otherwise, the question will be prompted to the user.
    """
    if actual_value is not None:
        return actual_value
    if fast:
        return default
    return question_func(text, default=default)
