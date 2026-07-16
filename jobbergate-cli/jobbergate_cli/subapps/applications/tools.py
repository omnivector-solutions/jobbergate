"""
Provide tool functions for working with Application data.
"""

import contextlib
import copy
import io
import pathlib
import tempfile
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, List, Optional, cast

import yaml
from loguru import logger

from jobbergate_cli.cache import ClientScopedCache
from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_SUPPORTED_FILES,
    FileType,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import render_dict
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
from jobbergate_core.sdk import Apps

CONTENT_TYPE_TEXT_PLAIN = "text/plain"
INVALID_APPLICATION_MODULE = "Invalid application module"

# In-memory cache of application runtimes keyed per client, so that repeated job-script
# creation in the same process (e.g. nested creation from within an application) does not
# re-download the same data. Each entry covers both the application details and the workflow
# source code. Plain data fetches (``fetch_application_data``) are deliberately not cached,
# so commands that display or mutate applications always see fresh data.
_application_runtime_cache: ClientScopedCache["ApplicationRuntime"] = ClientScopedCache()


def clear_application_runtime_cache() -> None:
    """
    Clear all cached application runtimes for all clients.
    """
    _application_runtime_cache.clear()


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


def _fetch_workflow_source_code(jg_ctx: ContextProtocol, app_data: ApplicationResponse) -> str:
    """
    Download the source code of the workflow file for an application.

    Args:
        jg_ctx: The Jobbergate context.
        app_data: The application data whose workflow file should be fetched.

    Raises:
        Abort: If the application does not have a workflow file.

    Returns:
        The source code of the application's workflow file.
    """
    if not app_data.workflow_files:
        raise Abort(
            f"Application {app_data.application_id} does not have a workflow file",
            subject="Workflow file not found",
            log_message="Application does not have a workflow file",
        )

    # A directory is used instead of a NamedTemporaryFile so the file is not already
    # open when make_request writes to it (re-opening an open file fails on Windows)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file_path = pathlib.Path(tmp_dir) / "jobbergate.py"
        make_request(
            jg_ctx.client,
            app_data.workflow_files[0].path,
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve application module file from API",
            save_to_file=tmp_file_path,
        )

        return tmp_file_path.read_text()


def fetch_application_runtime(jg_ctx: ContextProtocol, id_or_identifier: int | str) -> "ApplicationRuntime":
    """
    Fetch (or reuse from the per-client cache) the ``ApplicationRuntime`` for an application.

    The runtime bundles the application details and the workflow source code, so both are
    covered by a single cache entry. The returned runtime holds no execution state (see
    :meth:`ApplicationRuntime.run`), so the same instance can be shared and executed multiple
    times; treat it and its ``app_data`` as read-only, since any mutation would poison every
    later use in the same process. Use ``clear_application_runtime_cache`` to reset the cache.

    Args:
        jg_ctx: The JobbergateContext. Needed to access the Httpx client with which to make API calls.
        id_or_identifier: The id or identifier of the application to fetch.

    Returns:
        The ApplicationRuntime for the application.
    """
    runtime = _application_runtime_cache.get(jg_ctx.client, id_or_identifier)

    if runtime is None:
        app_data = fetch_application_data(jg_ctx, id_or_identifier)
        app_source_code = _fetch_workflow_source_code(jg_ctx, app_data)
        runtime = ApplicationRuntime(app_data, app_source_code)
        _application_runtime_cache.set(
            jg_ctx.client, id_or_identifier, runtime, app_data.application_id, app_data.identifier
        )

    return runtime


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
                (path.name, stack.enter_context(io.open(path, mode="r", newline="")), CONTENT_TYPE_TEXT_PLAIN),
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
                files={"upload_file": (relative_template_path.name, template_file, CONTENT_TYPE_TEXT_PLAIN)},
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
                "upload_file": (module_file_path.name, module_file, CONTENT_TYPE_TEXT_PLAIN),
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
    app_locals: Dict[str, Any] = {}
    exec(app_source, app_locals, app_locals)
    return app_locals["JobbergateApplication"]


@dataclass
class ApplicationRuntimeResult:
    """
    The outcome of a single execution of a Jobbergate application question workflow.

    Args:
        answers: The answers gathered from the question workflow.
        app_config: The application config resulting from the execution (legacy applications
            may change config values at runtime).
    """

    answers: Dict[str, Any]
    app_config: JobbergateApplicationConfig

    def as_flatten_param_dict(self) -> Dict[str, Any]:
        """Flatten the resulting config to support the rendering process."""
        param_dict_flat = {}
        for outer_value in self.app_config.model_dump().values():
            for nest_key, nest_value in outer_value.items():
                param_dict_flat[nest_key] = nest_value
        return param_dict_flat


@dataclass
class ApplicationRuntime:
    """
    Prepare and execute a Jobbergate application, gathering the answers to its questions.

    Instances hold only the immutable inputs (application data and source code); treat them
    as read-only, since the same instance may be cached and shared. Each call to :meth:`run`
    re-executes the source code on a fresh application instance and returns the outcome, so
    the same runtime can be executed multiple times without leaking state between runs.

    Args:
        app_data: The application data, can be either an ApplicationResponse or a LocalApplication.
        app_source_code: The source code of the application, often coming from jobbergate.py file.
        app_class: Optional override for the application class, skipping the source execution.
    """

    app_data: ApplicationResponse | LocalApplication
    app_source_code: str
    app_class: Optional[type[JobbergateApplicationBase]] = None

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
            ) from err

    def _build_app_module(self, sdk: Optional[Apps]) -> JobbergateApplicationBase:
        """
        Instantiate a fresh JobbergateApplication for a single execution of the workflow.

        The source code is re-executed on every call, so module-level and class-level state
        in the application can not leak from one execution to the next.
        """
        try:
            app_class = (
                self.app_class if self.app_class is not None else load_application_from_source(self.app_source_code)
            )
            return app_class(jobbergate_yaml=self.app_config.model_dump(), sdk=sdk)
        except Exception as err:
            raise Abort(
                "The application source fetched from the API is not valid",
                subject=INVALID_APPLICATION_MODULE,
                support=True,
                log_message=INVALID_APPLICATION_MODULE,
                original_error=err,
            ) from err

    def run(
        self,
        *,
        sdk: Optional[Apps] = None,
        supplied_params: Optional[Dict[str, Any]] = None,
        fast_mode: bool = False,
    ) -> ApplicationRuntimeResult:
        """
        Execute the jobbergate application python module.

        The runtime itself is not modified, so ``run`` can be called multiple times on the
        same (possibly cached) instance.

        Args:
            sdk: The SDK handed to the application instance for this execution. It is not
                stored on the runtime, so cached runtimes hold no reference to any client.
            supplied_params: Parameters supplied upfront; matching questions are not asked.
            fast_mode: Whether to use default answers (when available) instead of asking the user.

        Returns:
            The result carrying the gathered answers and the resulting application config.
        """
        app_module = self._build_app_module(sdk)
        try:
            result = self._gather_answers(app_module, dict(supplied_params or {}), fast_mode)
        except Abort:
            logger.exception("The question workflow aborted while executing the application")
            raise
        except Exception as err:
            logger.exception("The question workflow failed with an unexpected runtime error")
            raise Abort(
                "The question workflow failed to execute. Please check the log file for more information.",
                subject=f"Runtime error on application execution - {type(err).__name__}",
                support=True,
                log_message=f"The question workflow failed to execute: {err}",
                original_error=err,
            ) from err

        self._update_template_files_information(result.app_config)
        return result

    def _gather_answers(
        self,
        app_module: JobbergateApplicationBase,
        supplied_params: Dict[str, Any],
        fast_mode: bool,
    ) -> ApplicationRuntimeResult:
        """Gather the parameter values by executing the application methods."""
        logger.debug("Gathering answers from the application")
        answers = dict(supplied_params)
        # config should be the answers ideally
        # but we use app_module.jobbergate_config for backward compatibility with v1
        config = app_module.jobbergate_config
        config.update(supplied_params)

        next_method = "mainflow"

        while next_method is not None:
            method_to_call = getattr(app_module, next_method)
            logger.debug(f"Calling method {next_method}")
            try:
                workflow_questions = method_to_call(data=config)
            except NotImplementedError as err:
                raise Abort(
                    f"""
                    Abstract method not implemented.

                    Please implement {next_method} in your class.",
                    """,
                    subject=INVALID_APPLICATION_MODULE,
                ) from err

            prompts = []
            auto_answers = {}

            if workflow_questions is None:
                logger.warning(
                    "Deprecation warning: Application method {} returned None while a list is expected", next_method
                )
                workflow_questions = []

            for question in workflow_questions:
                if question.variablename in supplied_params:
                    continue
                elif fast_mode and question.default is not None:
                    auto_answers[question.variablename] = question.default
                else:
                    prompts.extend(question.make_prompts())

            workflow_answers = cast(Dict[str, Any], inquirer.prompt(prompts, raise_keyboard_interrupt=True))
            workflow_answers.update(auto_answers)

            logger.debug(f"Answers gathered from {next_method}: {workflow_answers}")

            config.update(workflow_answers)
            answers.update(workflow_answers)
            if len(auto_answers) > 0:
                render_dict(auto_answers, title="Default values used")

            next_method = config.pop("nextworkflow", None)

        # Legacy applications change the values at runtime, so the resulting config is rebuilt
        # from the application instance instead of reusing the initial one
        app_config = JobbergateApplicationConfig(
            application_config=dict(app_module.application_config),
            jobbergate_config=JobbergateConfig.model_validate(app_module.jobbergate_config),
        )
        logger.debug(f"Concluded getting answers: {answers}")
        return ApplicationRuntimeResult(answers=answers, app_config=app_config)

    def _update_template_files_information(self, app_config: JobbergateApplicationConfig) -> None:
        """Update the information about the template files if not already present in the configuration."""
        if not app_config.jobbergate_config.default_template:
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
            app_config.jobbergate_config.default_template = list_of_entrypoints[0]

        if app_config.jobbergate_config.supporting_files is None:
            list_of_supporting_files = [
                i.filename for i in self.app_data.template_files if i.file_type.upper() == "SUPPORT"
            ]
            if list_of_supporting_files:
                app_config.jobbergate_config.supporting_files = list_of_supporting_files
