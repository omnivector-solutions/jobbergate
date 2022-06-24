"""
Provide tool functions for working with Application data.
"""

import ast
import copy
import pathlib
import tarfile
import tempfile
from typing import Any, Dict, Optional, Tuple, cast

import yaml
from loguru import logger

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    TAR_NAME,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ApplicationResponse, JobbergateApplicationConfig, JobbergateContext
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import gather_param_values
from jobbergate_cli.text_tools import unwrap


def validate_application_files(application_path: pathlib.Path):
    """
    Validate application files at a given directory.

    Confirms:
        application_path exists
        application_path contains an application python module
        application_path contains an application configuration file
    """
    with Abort.check_expressions(
        f"The application files in {application_path} were invalid",
        raise_kwargs=dict(
            subject="Invalid application files",
            log_message=f"Application files located at {application_path} failed validation",
        ),
    ) as checker:
        checker(
            application_path.exists(),
            f"Application directory {application_path} does not exist",
        )

        application_module = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        checker(
            application_module.exists(),
            unwrap(
                f"""
                Application directory does not contain required application module
                {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}
                """
            ),
        )
        try:
            ast.parse(application_module.read_text())
            is_valid_python = True
        except Exception:
            is_valid_python = False
        checker(is_valid_python, f"The application module at {application_module} is not valid python code")

        application_config = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        checker(
            application_config.exists(),
            unwrap(
                f"""
                Application directory does not contain required configuration file
                {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}
                """
            ),
        )
        try:
            yaml.safe_load(application_config.read_text())
            is_valid_yaml = True
        except Exception:
            is_valid_yaml = False
        checker(is_valid_yaml, f"The application config at {application_config} is not valid YAML")


def load_default_config() -> Dict[str, Any]:
    """
    Load the default config for an application.
    """
    return copy.deepcopy(JOBBERGATE_APPLICATION_CONFIG)


def dump_full_config(application_path: pathlib.Path) -> str:
    """
    Dump the application config as text. Add existing template file paths into the config.
    """
    config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config = yaml.safe_load(config_path.read_text())
    config["jobbergate_config"]["template_files"] = sorted(
        str(t) for t in JobbergateApplicationBase.find_templates(application_path)
    )
    return yaml.dump(config)


def read_application_module(application_path: pathlib.Path) -> str:
    """
    Read the text from the application module found in the supplied application path.
    """
    module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    return module_path.read_text()


def build_application_tarball(application_path: pathlib.Path, build_dir: pathlib.Path) -> pathlib.Path:
    """
    Build a gzipped tarball from the files found at the target application path.

    :param: application_path: The directory where the application files may be found
    :param: build_dir:        The directory where the applicaiton files should be staged and zipped
    """
    tar_path = build_dir / TAR_NAME
    with tarfile.open(str(tar_path), "w|gz") as archive:
        module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        archive.add(module_path, arcname=f"/{module_path.name}")

        config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        archive.add(config_path, arcname=f"/{config_path.name}")

        template_root_path = application_path / "templates"
        if template_root_path.exists():
            for template_path in template_root_path.iterdir():
                if template_path.is_file:
                    rel_path = template_path.relative_to(application_path)
                    archive.add(template_path, arcname=f"/{rel_path}")
    return tar_path


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
    url = f"/jobbergate/applications/{id}"
    params = dict()
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
        url = "/jobbergate/applications"
        params["identifier"] = identifier

    # Make static type checkers happy
    assert jg_ctx.client is not None

    stub = f"id={id}" if id is not None else f"identifier={identifier}"
    return cast(
        ApplicationResponse,
        make_request(
            jg_ctx.client,
            url,
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve application {stub} from API",
            response_model_cls=ApplicationResponse,
            support=True,
            params=params,
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

    try:
        app_module = load_application_from_source(app_data.application_file, app_config)
    except Exception as err:
        raise Abort(
            "The application source fetched from the API is not valid",
            subject="Invalid application config",
            support=True,
            log_message="Invalid application module",
            original_error=err,
        )

    return (app_config, app_module)


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

    with tempfile.TemporaryDirectory() as temp_dir_str:
        build_path = pathlib.Path(temp_dir_str)
        logger.debug("Building application tar file at {build_path}")
        tar_path = build_application_tarball(application_path, build_path)
        response_code = cast(
            int,
            make_request(
                jg_ctx.client,
                f"/jobbergate/applications/{application_id}/upload",
                "POST",
                expect_response=False,
                abort_message="Request to upload application files was not accepted by the API",
                support=True,
                files=dict(upload_file=open(tar_path, "rb")),
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

    Creates the module in a temporary file and importins it with importlib.

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
