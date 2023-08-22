"""
Provide tool functions for working with Application data.
"""

import contextlib
import copy
import io
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple, cast

import yaml
from loguru import logger

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_SUPPORTED_FILES,
    FileType,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ApplicationResponse, JobbergateApplicationConfig, JobbergateConfig, JobbergateContext
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import gather_param_values


def load_default_config() -> Dict[str, Any]:
    """
    Load the default config for an application.
    """
    return copy.deepcopy(JOBBERGATE_APPLICATION_CONFIG)


def fetch_application_data(
    jg_ctx: JobbergateContext,
    id: Optional[int] = None,
    identifier: Optional[str] = None,
) -> ApplicationResponse:
    """
    Retrieve an application from the API by ``id`` or ``identifier``.

    :param: jg_ctx:     The JobbergateContext. Needed to access the Httpx client with which to make API calls
    :param: id:         The id of the application to fetch
    :param: identifier: If supplied, look for an application instance with the provided identifier
    :returns: An instance of ApplicationResponse containing the application data
    """
    identification: Any = id
    if id is None and identifier is None:
        raise Abort(
            """
            You must supply either [yellow]id[/yellow] or [yellow]identifier[/yellow].
            """,
            subject="Invalid params",
            warn_only=True,
        )
    elif id is not None and identifier is not None:
        raise Abort(
            """
            You may not supply both [yellow]id[/yellow] and [yellow]identifier[/yellow].
            """,
            subject="Invalid params",
            warn_only=True,
        )
    elif identifier is not None:
        identification = identifier

    # Make static type checkers happy
    assert jg_ctx.client is not None

    stub = f"id={id}" if id is not None else f"identifier={identifier}"
    return cast(
        ApplicationResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-script-templates/{identification}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve application {stub} from API",
            response_model_cls=ApplicationResponse,
            support=True,
        ),
    )


def load_application_data(
    app_data: ApplicationResponse,
    application_source_file: str,
) -> Tuple[JobbergateApplicationConfig, JobbergateApplicationBase]:
    """
    Validates and loads the data for an application returned from the API's applications GET endpoint.

    As part of the Jobbergate data restructure, sections of the legacy jobbergate.yaml
    are now stored in different tables in the backend. This function reconstructs
    them from app_data.workflow_file.runtime_config and app_data.template_vars
    for backward compatibility.

    :param: app_data: A dictionary containing the application data
    :returns: A tuple containing the application config and the application module
    """
    if not app_data.workflow_files:  # make type checker happy
        raise Abort(
            "No workflow file found in application data",
            subject="Invalid application data",
            log_message="No workflow file found in application data",
        )
    try:
        app_config = JobbergateApplicationConfig(
            jobbergate_config=JobbergateConfig(**app_data.workflow_files[0].runtime_config),
            application_config=app_data.template_vars,
        )
    except Exception as err:
        logger.error("ERR: ", err)
        raise Abort(
            "The application config fetched from the API is not valid",
            subject="Invalid application config",
            support=True,
            log_message="Invalid application config",
            original_error=err,
        )

    try:
        app_module = load_application_from_source(application_source_file, app_config)
    except Exception as err:
        raise Abort(
            "The application source fetched from the API is not valid",
            subject="Invalid application module",
            support=True,
            log_message="Invalid application module",
            original_error=err,
        )

    return (app_config, app_module)


@contextlib.contextmanager
def get_upload_files(application_path: pathlib.Path):
    """
    Context manager to build the ``files`` parameter.

    Open the supplied file(s) and build a ``files`` param appropriate for using
    multi-part file uploads with the client.
    """
    Abort.require_condition(application_path.is_dir(), f"Application directory {application_path} does not exist")

    with contextlib.ExitStack() as stack:
        yield [
            (
                "upload_files",
                (path.name, stack.enter_context(io.open(path, mode="r", newline="")), "text/plain"),
            )
            for path in application_path.rglob("*")
            if path.is_file() and path.suffix in JOBBERGATE_APPLICATION_SUPPORTED_FILES
        ]


def upload_application(
    jg_ctx: JobbergateContext,
    application_path: pathlib.Path,
    application_id: int,
) -> bool:
    """
    Upload an application given an application path and the application id.

    :param: jg_ctx:           The JobbergateContext. Needed to access the Httpx client with which to make API calls
    :param: application_path: The directory where the application files to upload may be found
    :param: application_id:   The id of the application for which to upload  data
    :returns: True if the upload was successful; False otherwise
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None

    Abort.require_condition(application_path.is_dir(), f"Application directory {application_path} does not exist")

    config_file_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    Abort.require_condition(config_file_path.is_file(), f"Application config file {config_file_path} does not exist")

    module_file_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    Abort.require_condition(module_file_path.is_file(), f"Application module file {module_file_path} does not exist")

    template_files_set = set(application_path.rglob("*.j2")) | set(application_path.rglob("*.jinja2"))
    Abort.require_condition(template_files_set, f"No template files found in {application_path}")

    application_config = load_application_config_from_source(config_file_path.read_text())

    logger.debug("Preparing to upload the template configuration")

    response_code = cast(
        int,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-script-templates/{application_id}",
            "PUT",
            expect_response=False,
            abort_message="Request to upload application configuration was not accepted by the API",
            support=True,
            json={"template_vars": application_config.application_config},
        ),
    )

    if response_code != 200:
        return False

    supporting_files = application_config.jobbergate_config.supporting_files or []

    for complete_template_path in template_files_set:
        relative_template_path = complete_template_path.relative_to(application_path)
        logger.debug(f"Preparing to upload {relative_template_path}")

        with open(complete_template_path, "rb") as template_file:
            if relative_template_path.as_posix() in supporting_files:
                file_type = FileType.SUPPORT
            else:
                file_type = FileType.ENTRYPOINT

            response_code = cast(
                int,
                make_request(
                    jg_ctx.client,
                    f"/jobbergate/job-script-templates/{application_id}/upload/template/{file_type}",
                    "PUT",
                    expect_response=False,
                    abort_message="Request to upload application files was not accepted by the API",
                    support=True,
                    files={"upload_file": (relative_template_path.name, template_file, "text/plain")},
                ),
            )
            if response_code != 200:
                return False

    logger.debug(f"Preparing to upload {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}")
    with open(module_file_path, "rb") as module_file:
        response_code = cast(
            int,
            make_request(
                jg_ctx.client,
                f"/jobbergate/job-script-templates/{application_id}/upload/workflow",
                "PUT",
                expect_response=False,
                abort_message="Request to upload application module was not accepted by the API",
                support=True,
                files={
                    "upload_file": (module_file_path.name, module_file, "text/plain"),
                },
                data={"runtime_config": application_config.jobbergate_config.json()},
            ),
        )
    if response_code != 200:
        return False

    return True


def save_application_files(
    jg_ctx: JobbergateContext,
    application_data: ApplicationResponse,
    destination_path: pathlib.Path,
) -> List[pathlib.Path]:
    """
    Save the application files from the API response into a local destination.
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None

    logger.debug(f"Saving application files to {destination_path.as_posix()}")
    saved_files: List[pathlib.Path] = []

    if application_data.workflow_files:
        application_config = JobbergateApplicationConfig(
            application_config=application_data.template_vars,
            jobbergate_config=JobbergateConfig(**application_data.workflow_files[0].runtime_config),
        )
        config_path = destination_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.dump(
                json.loads(  # workaround to convert path to string
                    application_config.json(
                        exclude_none=True,
                        exclude_unset=True,
                    ),
                ),
                indent=2,
            )
        )
        saved_files.append(config_path)

    for template_file in application_data.template_files:
        template_path = destination_path / "templates" / template_file.filename
        make_request(
            jg_ctx.client,
            template_file.path,
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve template file {template_file.filename} from API",
            save_to_file=template_path,
        )
        saved_files.append(template_path)

    if application_data.workflow_files:
        workflow_path = destination_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        make_request(
            jg_ctx.client,
            application_data.workflow_files[0].path,
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve application module file from API",
            save_to_file=workflow_path,
        )
        saved_files.append(workflow_path)

    logger.debug(f"The following files were saved: {list(map(str, saved_files))}")
    return saved_files


def load_application_config_from_source(config_source: str) -> JobbergateApplicationConfig:
    """
    Load the JobbergateApplicationConfig from a text string containing the config as YAML.

    :param: config_source: The YAML containing the config
    :returns: A JobbergateApplicationConfig instance with the config values
    """
    config_data = yaml.safe_load(config_source)
    config = JobbergateApplicationConfig(**config_data)
    return config


def load_application_from_source(app_source: str, app_config: JobbergateApplicationConfig) -> JobbergateApplicationBase:
    """
    Load the JobbergateApplication class from a text string containing the source file.

    Creates the module in a temporary file and imports it with importlib.

    Adapted from: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

    :param: app_source: The JobbergateApplication source code to load
    :param: app_config: The JobbergateApplicationConfig needed to instantiate the JobbergateApplication
    """
    app_locals: Dict[str, Any] = dict()
    exec(app_source, app_locals, app_locals)
    jobbergate_application_class = app_locals["JobbergateApplication"]
    application = jobbergate_application_class(app_config.dict())
    return application


def execute_application(
    app_module: JobbergateApplicationBase,
    app_config: JobbergateApplicationConfig,
    supplied_params: Optional[Dict[str, Any]] = None,
    fast_mode: bool = False,
):
    """
    Execute the jobbergate application python module.

    Updates the app_config with values gathered in the question workflow

    :param: app_module:      The source code for the application to execute
    :param: app_config:      The configuration for the JobbergateApplication
    :param: supplied_params: Pre-set values for the parameters. Any questions about these values will be skipped.
    :param: fast_mode:       If true, do not ask the user questions. Just use supplied_params or defaults
    :returns: The configuration values collected from the user by executing the application
    """
    app_params = gather_param_values(app_module, supplied_params=supplied_params, fast_mode=fast_mode)
    app_config.application_config.update(**app_params)
    return app_params
