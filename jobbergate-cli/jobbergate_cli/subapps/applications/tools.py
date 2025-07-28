"""
Provide tool functions for working with Application data.
"""

import contextlib
import copy
import io
import pathlib
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, List, Union, cast

import yaml
from jobbergate_core.sdk import Apps
from loguru import logger

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_SUPPORTED_FILES,
    FileType,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import render_dict, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import (
    ApplicationResponse,
    ContextProtocol,
    JobbergateApplicationConfig,
    JobbergateConfig,
    LocalApplication,
    LocalTemplateFile,
    LocalWorkflowFile,
)
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import inquirer


def load_default_config() -> Dict[str, Any]:
    """
    Load the default config for an application.
    """
    return copy.deepcopy(JOBBERGATE_APPLICATION_CONFIG)


def fetch_application_data_locally(
    application_path: pathlib.Path,
) -> LocalApplication:
    """
    Retrieve an application from a local directory.

    Args:
        application_path: The directory containing the application files.

    Returns:
        A LocalApplication instance containing the application data.
    """
    Abort.require_condition(application_path.is_dir(), f"Application directory {application_path} does not exist")

    config_file_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    Abort.require_condition(
        config_file_path.is_file(), f"Application config file {JOBBERGATE_APPLICATION_CONFIG_FILE_NAME} does not exist"
    )

    module_file_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    Abort.require_condition(
        module_file_path.is_file(), f"Application module file {JOBBERGATE_APPLICATION_MODULE_FILE_NAME} does not exist"
    )

    template_files_set = set(application_path.rglob("*.j2")) | set(application_path.rglob("*.jinja2"))
    Abort.require_condition(template_files_set, f"No template files found in {application_path}")

    application_config = load_application_config_from_source(config_file_path.read_text())

    supporting_files = application_config.jobbergate_config.supporting_files or []

    template_files = []

    for complete_template_path in template_files_set:
        relative_template_path = complete_template_path.relative_to(application_path)

        if relative_template_path.as_posix() in supporting_files:
            file_type = FileType.SUPPORT
        else:
            file_type = FileType.ENTRYPOINT

        template_files.append(
            LocalTemplateFile(
                filename=relative_template_path.name,
                path=complete_template_path,
                file_type=file_type,
            )
        )

    workflow_file = LocalWorkflowFile(
        filename=module_file_path.name,
        path=module_file_path,
        runtime_config=application_config.jobbergate_config.model_dump(),
    )

    return LocalApplication(
        template_vars=application_config.application_config,
        template_files=template_files,
        workflow_files=[workflow_file],
    )


def fetch_application_data(jg_ctx: ContextProtocol, id_or_identifier: int | str) -> ApplicationResponse:
    """
    Retrieve an application from the API by id or identifier.

    Args:
        jg_ctx: The JobbergateContext. Needed to access the Httpx client with which to make API calls.
        id: The id of the application to fetch.
        identifier: If supplied, look for an application instance with the provided identifier.

    Returns:
        An instance of ApplicationResponse containing the application data.
    """
    stub = f"id={id_or_identifier}" if isinstance(id_or_identifier, int) else f"identifier={id_or_identifier}"
    return cast(
        ApplicationResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-script-templates/{id_or_identifier}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve application {stub} from API",
            response_model_cls=ApplicationResponse,
            support=True,
        ),
    )


@contextlib.contextmanager
def get_upload_files(application_path: pathlib.Path):
    """
    Context manager to build the files parameter.

    Open the supplied file(s) and build a files param appropriate for using
    multi-part file uploads with the client.

    Args:
        application_path: The directory where the application files are located.
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
    jg_ctx: ContextProtocol,
    application_path: pathlib.Path,
    id_or_identifier: int | str,
):
    """
    Upload an application given an application path and the application id.

    Args:
        jg_ctx: The JobbergateContext. Needed to access the Httpx client with which to make API calls.
        application_path: The directory where the application files to upload may be found.
        application_id: The id of the application for which to upload data.
        application_identifier: The identifier of the application for which to upload data.
    """
    Abort.require_condition(application_path.is_dir(), f"Application directory {application_path} does not exist")

    config_file_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    Abort.require_condition(config_file_path.is_file(), f"Application config file {config_file_path} does not exist")

    module_file_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    Abort.require_condition(module_file_path.is_file(), f"Application module file {module_file_path} does not exist")

    template_files_set = set(application_path.rglob("*.j2")) | set(application_path.rglob("*.jinja2"))
    Abort.require_condition(template_files_set, f"No template files found in {application_path}")

    application_config = load_application_config_from_source(config_file_path.read_text())

    logger.debug("Preparing to upload the template configuration")

    make_request(
        jg_ctx.client,
        f"/jobbergate/job-script-templates/{id_or_identifier}",
        "PUT",
        expect_response=False,
        abort_message="Request to upload application configuration was not accepted by the API",
        support=True,
        json={"template_vars": application_config.application_config},
        expected_status=200,
    )

    supporting_files = application_config.jobbergate_config.supporting_files or []

    for complete_template_path in template_files_set:
        relative_template_path = complete_template_path.relative_to(application_path)
        logger.debug(f"Preparing to upload {relative_template_path}")

        with open(complete_template_path, "rb") as template_file:
            if relative_template_path.as_posix() in supporting_files:
                file_type = FileType.SUPPORT
            else:
                file_type = FileType.ENTRYPOINT

            make_request(
                jg_ctx.client,
                f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{file_type.value}",
                "PUT",
                expect_response=False,
                abort_message="Request to upload application files was not accepted by the API",
                support=True,
                files={"upload_file": (relative_template_path.name, template_file, "text/plain")},
                expected_status=200,
            )

    logger.debug(f"Preparing to upload {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}")
    with open(module_file_path, "rb") as module_file:
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
            "PUT",
            expect_response=False,
            abort_message="Request to upload application module was not accepted by the API",
            support=True,
            files={
                "upload_file": (module_file_path.name, module_file, "text/plain"),
            },
            data={"runtime_config": application_config.jobbergate_config.model_dump_json()},
            expected_status=200,
        )


def save_application_files(
    jg_ctx: ContextProtocol,
    application_data: ApplicationResponse,
    destination_path: pathlib.Path,
) -> List[pathlib.Path]:
    """
    Save the application files from the API response into a local destination.
    """

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
                application_config.model_dump(
                    mode="json",
                    exclude_none=True,
                    exclude_unset=True,
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

    Args:
        config_source: The YAML containing the config

    Returns:
        A JobbergateApplicationConfig instance with the config values
    """
    config_data = yaml.safe_load(config_source)
    config = JobbergateApplicationConfig(**config_data)
    return config


def load_application_from_source(app_source: str) -> type[JobbergateApplicationBase]:
    """
    Load the JobbergateApplication class from a text string containing the source file.

    Creates the module in a temporary file and imports it with importlib.

    Adapted from: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

    Args:
        app_source: The JobbergateApplication source code to load
    """
    app_locals: Dict[str, Any] = dict()
    exec(app_source, app_locals, app_locals)
    return app_locals["JobbergateApplication"]


@dataclass
class ApplicationRuntime:
    """
    Prepare and execute a Jobbergate application gathering the answers to the questions.

    Args:
        app_data: The application data, can be either an ApplicationResponse or a LocalApplication.
        app_source_code: The source code of the application, often coming from jobbergate.py file.
        supplied_params: The parameters supplied to the application, defaults to an empty dictionary.
        fast_mode: A flag indicating whether the application is in fast mode, defaults to False.
    """

    app_data: Union[ApplicationResponse, LocalApplication]
    app_source_code: str
    sdk: Apps
    supplied_params: Dict[str, Any] = field(default_factory=dict)
    fast_mode: bool = False

    def __post_init__(self) -> None:
        self.answers: Dict[str, Any] = dict()

    @cached_property
    def app_config(self) -> JobbergateApplicationConfig:
        """
        The JobbergateApplicationConfig for the application.
        """
        if not self.app_data.workflow_files:  # make type checker happy
            raise Abort(
                "No workflow file found in application data",
                subject="Invalid application data",
                log_message="No workflow file found in application data",
            )
        try:
            return JobbergateApplicationConfig(
                jobbergate_config=JobbergateConfig(**self.app_data.workflow_files[0].runtime_config),
                application_config=self.app_data.template_vars,
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

    @cached_property
    def app_module(self) -> JobbergateApplicationBase:
        """
        The JobbergateApplicationBase for the application.
        """
        try:
            jobbergate_application_class = load_application_from_source(self.app_source_code)
            return jobbergate_application_class(jobbergate_yaml=self.app_config.model_dump(), sdk=self.sdk)
        except Exception as err:
            raise Abort(
                "The application source fetched from the API is not valid",
                subject="Invalid application module",
                support=True,
                log_message="Invalid application module",
                original_error=err,
            )

    def execute_application(self):
        """Execute the jobbergate application python module."""
        try:
            self._gather_answers()
        except Exception as err:
            exception_name = type(err).__name__
            terminal_message(
                "The question workflow failed to execute. Please check the traceback bellow for more information.",
                subject=f"Runtime error on application execution - {exception_name}",
                color="red",
            )
            raise err

        self._update_template_files_information()

    def as_flatten_param_dict(self) -> Dict[str, Any]:
        """Flatten the internal data to support the rendering process."""
        param_dict_flat = {}
        for outer_value in self.app_config.model_dump().values():
            for nest_key, nest_value in outer_value.items():
                param_dict_flat[nest_key] = nest_value
        return param_dict_flat

    def _gather_answers(self):
        """Gather the parameter values by executing the application methods."""
        logger.debug("Gathering answers from the application")
        self.answers.update(self.supplied_params)
        # config should be self.answers ideally
        # but we use self.app_module.jobbergate_config for backward compatibility with v1
        config = self.app_module.jobbergate_config
        config.update(self.supplied_params)

        next_method = "mainflow"

        while next_method is not None:
            method_to_call = getattr(self.app_module, next_method)
            logger.debug(f"Calling method {next_method}")
            try:
                workflow_questions = method_to_call(data=config)
            except NotImplementedError:
                raise Abort(
                    f"""
                    Abstract method not implemented.

                    Please implement {next_method} in your class.",
                    """,
                    subject="Invalid application module",
                )

            prompts = []
            auto_answers = {}

            if workflow_questions is None:
                logger.warning(
                    "Deprecation warning: Application method {} returned None while a list is expected", next_method
                )
                workflow_questions = []

            for question in workflow_questions:
                if question.variablename in self.supplied_params:
                    continue
                elif self.fast_mode and question.default is not None:
                    auto_answers[question.variablename] = question.default
                else:
                    prompts.extend(question.make_prompts())

            workflow_answers = cast(Dict[str, Any], inquirer.prompt(prompts, raise_keyboard_interrupt=True))
            workflow_answers.update(auto_answers)

            logger.debug(f"Answers gathered from {next_method}: {workflow_answers}")

            config.update(workflow_answers)
            self.answers.update(workflow_answers)
            if len(auto_answers) > 0:
                render_dict(auto_answers, title="Default values used")

            next_method = config.pop("nextworkflow", None)

        # Legacy applications change the values at runtime, so we need to update the config
        self.app_config = JobbergateApplicationConfig(
            application_config=dict(self.app_module.application_config),
            jobbergate_config=JobbergateConfig.model_validate(self.app_module.jobbergate_config),
        )
        logger.debug(f"Concluded getting answers: {self.answers}")

    def _update_template_files_information(self):
        """Update the information about the template files if not already present in the configuration."""
        if not self.app_config.jobbergate_config.default_template:
            list_of_entrypoints = [
                i.filename for i in self.app_data.template_files if i.file_type.upper() == "ENTRYPOINT"
            ]
            if len(list_of_entrypoints) != 1:
                raise Abort(
                    f"""
                    Application does not have one entry point, found {len(list_of_entrypoints)}",
                    """,
                    subject="Entry point is unspecified",
                    log_message="Entry point file not specified",
                )
            self.app_config.jobbergate_config.default_template = list_of_entrypoints[0]

        if self.app_config.jobbergate_config.supporting_files is None:
            list_of_supporting_files = [
                i.filename for i in self.app_data.template_files if i.file_type.upper() == "SUPPORT"
            ]
            if list_of_supporting_files:
                self.app_config.jobbergate_config.supporting_files = list_of_supporting_files
