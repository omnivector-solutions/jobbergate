"""
Provide tool functions for working with Application data.
"""

import contextlib
import copy
import io
import pathlib
from typing import Any, Dict, Optional, Tuple, cast

import yaml
from loguru import logger

from jobbergate_cli.constants import JOBBERGATE_APPLICATION_CONFIG, JOBBERGATE_APPLICATION_SUPPORTED_FILES
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ApplicationResponse, JobbergateApplicationConfig, JobbergateContext
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
            f"/jobbergate/applications/{identification}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve application {stub} from API",
            response_model_cls=ApplicationResponse,
            support=True,
        ),
    )


def load_application_data(
    app_data: ApplicationResponse,
) -> Tuple[JobbergateApplicationConfig, JobbergateApplicationBase]:
    """
    Validates and loads the data for an application returned from the API's applications GET endpoint.

    :param: app_data: A dictionary containing the application data
    :returns: A tuple containing the application config and the application module
    """
    if not app_data.application_config:

        raise Abort(
            f"Fail to retrieve the application config file for id={app_data.id}",
            subject="Application config is missing",
            log_message="Application config is missing",
        )

    try:
        app_config = load_application_config_from_source(app_data.application_config)
    except Exception as err:
        print("ERR: ", err)
        raise Abort(
            "The application config fetched from the API is not valid",
            subject="Invalid application config",
            support=True,
            log_message="Invalid application config",
            original_error=err,
        )

    if not app_data.application_source_file:

        raise Abort(
            f"Fail to retrieve the application source file for id={app_data.id}",
            subject="Application source file is missing",
            log_message="Application source file is missing",
        )

    try:
        app_module = load_application_from_source(app_data.application_source_file, app_config)
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

    with get_upload_files(pathlib.Path(application_path)) as upload_files:
        logger.debug(
            f"Preparing to upload {len(upload_files)} application files from {application_path}",
        )
        response_code = cast(
            int,
            make_request(
                jg_ctx.client,
                f"/jobbergate/applications/{application_id}/upload",
                "POST",
                expect_response=False,
                abort_message="Request to upload application files was not accepted by the API",
                support=True,
                files=upload_files,
            ),
        )
        return response_code == 201


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
