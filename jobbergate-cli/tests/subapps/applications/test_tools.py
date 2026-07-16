import datetime
import gc
import importlib
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    FileType,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import (
    ApplicationResponse,
    JobbergateApplicationConfig,
    LocalApplication,
    LocalTemplateFile,
    LocalWorkflowFile,
    TemplateFileResponse,
    WorkflowFileResponse,
)
from jobbergate_cli.subapps.applications import tools as application_tools
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import Text
from jobbergate_cli.subapps.applications.tools import (
    ApplicationRuntime,
    ApplicationRuntimeResult,
    _application_runtime_cache,
    clear_application_runtime_cache,
    fetch_application_data,
    fetch_application_data_locally,
    fetch_application_runtime,
    load_application_config_from_source,
    load_default_config,
    save_application_files,
    upload_application,
)


@pytest.fixture(autouse=True)
def clean_application_runtime_cache():
    """Ensure each test in this module starts and ends with an empty application runtime cache."""
    clear_application_runtime_cache()
    yield
    clear_application_runtime_cache()


def test_load_default_config():
    default_config = load_default_config()
    assert default_config == JOBBERGATE_APPLICATION_CONFIG
    default_config["foo"] = "bar"
    assert default_config != JOBBERGATE_APPLICATION_CONFIG


def test_fetch_application_data__success__using_id(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    app_data = dummy_application_data[0]
    app_id = app_data["id"]
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{app_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, id_or_identifier=app_id)
    assert fetch_route.called
    assert result == ApplicationResponse.model_validate(app_data)


def test_fetch_application_data__success__using_identifier(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    app_data = dummy_application_data[0]
    app_identifier = app_data["identifier"]
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{app_identifier}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, id_or_identifier=app_identifier)
    assert fetch_route.called
    assert result == ApplicationResponse.model_validate(app_data)


def test_fetch_application_data__is_not_cached(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    """Plain data fetches always hit the API, so display/mutation commands never see stale data."""
    app_data = dummy_application_data[0]
    app_id = app_data["id"]
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{app_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    fetch_application_data(dummy_context, id_or_identifier=app_id)
    fetch_application_data(dummy_context, id_or_identifier=app_id)

    assert fetch_route.call_count == 2


def test_fetch_application_data_locally__success(
    dummy_module_source, dummy_config_source, dummy_template_source, tmp_path
):
    expected_config = load_application_config_from_source(dummy_config_source)

    config_file_path = tmp_path / "jobbergate.yaml"
    config_file_path.write_text(dummy_config_source)

    module_file_path = tmp_path / "jobbergate.py"
    module_file_path.write_text(dummy_module_source)

    template_file_path = tmp_path / "test-job-script.py.j2"
    template_file_path.write_text(dummy_template_source)

    result = fetch_application_data_locally(tmp_path)

    assert result == LocalApplication(
        template_vars=expected_config.application_config,
        template_files=[
            LocalTemplateFile(filename="test-job-script.py.j2", path=template_file_path, file_type=FileType.ENTRYPOINT)
        ],
        workflow_files=[
            LocalWorkflowFile(
                filename="jobbergate.py",
                path=module_file_path,
                runtime_config=expected_config.jobbergate_config.model_dump(),
            )
        ],
    )


def test_fetch_application_data_locally__fails_if_application_path_doesnt_exist():
    non_exist = pathlib.Path("/does/not/exist")
    with pytest.raises(Abort, match=f"Application directory {non_exist} does not exist"):
        fetch_application_data_locally(non_exist)


def test_fetch_application_data_locally_fails_if_config_file_not_found(tmp_path):
    module_file_path = tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    module_file_path.write_text("")

    template_file_path = tmp_path / "test-job-script.py.j2"
    template_file_path.write_text("")

    with pytest.raises(
        Abort, match=f"Application config file {JOBBERGATE_APPLICATION_CONFIG_FILE_NAME} does not exist"
    ):
        fetch_application_data_locally(tmp_path)


def test_fetch_application_data_locally_fails_if_module_file_not_found(tmp_path):
    config_file_path = tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config_file_path.write_text("")

    template_file_path = tmp_path / "test-job-script.py.j2"
    template_file_path.write_text("")

    with pytest.raises(
        Abort, match=f"Application module file {JOBBERGATE_APPLICATION_MODULE_FILE_NAME} does not exist"
    ):
        fetch_application_data_locally(tmp_path)


def test_fetch_application_data_locally_fails_if_no_template_files_found(tmp_path):
    config_file_path = tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config_file_path.write_text("")

    module_file_path = tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    module_file_path.write_text("")

    with pytest.raises(Abort, match="No template files found in"):
        fetch_application_data_locally(tmp_path)


class TestUploadApplicationFiles:
    """Test the upload_application_files function."""

    application_id = 1

    @pytest.fixture(scope="function")
    def mocked_routes(self, dummy_domain):
        app_mock = respx.mock(base_url=dummy_domain)

        app_mock.put(
            path=f"/jobbergate/job-script-templates/{self.application_id}",
            name="update",
        ).respond(httpx.codes.OK)

        app_mock.put(
            path=f"/jobbergate/job-script-templates/{self.application_id}/upload/template/ENTRYPOINT",
            name="upload_template",
        ).respond(httpx.codes.OK)

        app_mock.put(
            path=f"/jobbergate/job-script-templates/{self.application_id}/upload/workflow",
            name="upload_workflow",
        ).respond(httpx.codes.OK)

        yield app_mock

    @respx.mock(assert_all_called=True, assert_all_mocked=True)
    def test_upload_application__success(
        self,
        dummy_application_dir,
        dummy_context,
        mocked_routes,
    ):
        with mocked_routes as routes:
            upload_application(dummy_context, dummy_application_dir, self.application_id)

            # Ensure just the filename is included, nothing extra from path
            filename_check = b'filename="jobbergate.py"\r\n'
            assert routes["upload_workflow"].call_count == 1
            assert filename_check in routes["upload_workflow"].calls[0].request.content

            filename_check = b'filename="job-script-template.py.j2"\r\n'
            assert routes["upload_template"].call_count == 1
            assert filename_check in routes["upload_template"].calls[0].request.content

    @respx.mock(assert_all_mocked=True)
    def test_upload_application__fails_directory_does_not_exists(self, dummy_application_dir, dummy_context):
        application_path = dummy_application_dir / "does-not-exist"
        with pytest.raises(Abort, match="Application directory"):
            upload_application(dummy_context, application_path, self.application_id)

    @respx.mock(assert_all_mocked=True)
    def test_upload_application__fails_config_file_not_found(self, dummy_application_dir, dummy_context):
        file_path = dummy_application_dir / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        file_path.unlink()
        with pytest.raises(Abort, match="Application config file"):
            upload_application(dummy_context, dummy_application_dir, self.application_id)

    @respx.mock(assert_all_mocked=True)
    def test_upload_application__fails_module_file_not_found(self, dummy_application_dir, dummy_context):
        file_path = dummy_application_dir / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        file_path.unlink()
        with pytest.raises(Abort, match="Application module file"):
            upload_application(dummy_context, dummy_application_dir, self.application_id)

    @respx.mock(assert_all_mocked=True)
    def test_upload_application__fails_no_template_found(self, dummy_application_dir, dummy_context):
        file_path = dummy_application_dir / "templates" / "job-script-template.py.j2"
        file_path.unlink()
        with pytest.raises(Abort, match="No template files found in"):
            upload_application(dummy_context, dummy_application_dir, self.application_id)


class TestDownloadApplicationFiles:
    """
    Test the save_application_files function.
    """

    def test_save_application_files__no_files(self, tmp_path, dummy_context):
        """
        Test that the function returns an empty list if there are no files to download.
        """
        application_data = ApplicationResponse(
            id=1,
            name="dummy",
            owner_email="dummy@email.com",
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )

        desired_list_of_files = []

        assert save_application_files(dummy_context, application_data, tmp_path) == desired_list_of_files
        assert list(tmp_path.rglob("*")) == desired_list_of_files

    def test_save_application_files__all_files(
        self,
        respx_mock,
        dummy_domain,
        dummy_context,
        tmp_path,
        dummy_module_source,
        dummy_config_source,
        dummy_template_source,
    ):
        """
        Test that the function downloads all files.
        """

        application_config = load_application_config_from_source(dummy_config_source)

        application_data = ApplicationResponse(
            id=1,
            name="dummy",
            owner_email="dummy@email.com",
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            template_vars=application_config.application_config,
            template_files=[
                TemplateFileResponse(
                    filename="test-job-script.py.j2",
                    parent_id=1,
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                    file_type="ENTRYPOINT",
                )
            ],
            workflow_files=[
                WorkflowFileResponse(
                    filename="jobbergate.py",
                    parent_id=1,
                    runtime_config=application_config.jobbergate_config.model_dump(),
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                )
            ],
        )

        get_template_routes = [respx_mock.get(f"{dummy_domain}{t.path}") for t in application_data.template_files]
        for route in get_template_routes:
            route.mock(
                return_value=httpx.Response(
                    httpx.codes.OK,
                    content=dummy_template_source.encode(),
                ),
            )
        get_workflow_route = respx_mock.get(f"{dummy_domain}{application_data.workflow_files[0].path}")
        get_workflow_route.mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                content=dummy_module_source.encode(),
            ),
        )

        desired_list_of_files = [
            tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
            tmp_path / "templates" / "test-job-script.py.j2",
            tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
        ]

        assert save_application_files(dummy_context, application_data, tmp_path) == desired_list_of_files
        assert set(tmp_path.rglob("*")) == {tmp_path / "templates", *desired_list_of_files}

        actual_application_config = load_application_config_from_source(
            (tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME).read_text()
        )
        assert actual_application_config == application_config
        assert (tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME).read_text() == dummy_module_source
        assert (tmp_path / "templates" / "test-job-script.py.j2").read_text() == dummy_template_source


class TestApplicationRuntime:
    @pytest.fixture(scope="function")
    def application_runtime(self, dummy_module_source, dummy_application_data):
        return ApplicationRuntime(
            ApplicationResponse.model_validate(dummy_application_data[0]),
            dummy_module_source,
        )

    def test_flatten_param_dict__success(self, application_runtime):
        runtime_result = ApplicationRuntimeResult(answers={}, app_config=application_runtime.app_config)
        actual_result = runtime_result.as_flatten_param_dict()
        expected_result = {
            "template_files": None,
            "supporting_files_output_name": None,
            "supporting_files": None,
            "default_template": "test-job-script.py.j2",
            "foo": "bar",
        }

        assert actual_result == expected_result

    def test_get_app_config__success(self, application_runtime):
        expected_config = JobbergateApplicationConfig(
            application_config={"foo": "bar"},
            jobbergate_config={"default_template": "test-job-script.py.j2"},
        )

        assert application_runtime.app_config == expected_config

    def test_build_app_module__success(self, application_runtime):
        sdk = MagicMock()
        app_module = application_runtime._build_app_module(sdk)
        assert isinstance(app_module, JobbergateApplicationBase)
        assert getattr(app_module, "mainflow", None) is not None
        assert app_module.sdk == sdk
        assert app_module.jobbergate_config == application_runtime.app_config.jobbergate_config.model_dump()
        assert app_module.application_config == application_runtime.app_config.application_config

    def test_run__re_executes_the_source_code_on_every_run(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        """Module and class level state can not leak between runs, since the source is re-executed."""
        dummy_render_class.prepared_input = {"foo": "FOO", "bar": "BAR", "baz": "BAZ"}
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        load_spy = mocker.spy(
            importlib.import_module("jobbergate_cli.subapps.applications.tools"),
            "load_application_from_source",
        )

        application_runtime.run()
        application_runtime.run()

        assert load_spy.call_count == 2

    def test_run__basic(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        runtime_result = application_runtime.run()
        assert runtime_result.answers == {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }

    def test_run__with_supplied_params(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        runtime_result = application_runtime.run(supplied_params={"foo": "oof"})
        assert runtime_result.answers == {
            "foo": "oof",
            "bar": "BAR",
            "baz": "BAZ",
        }

    def test_run__with_fast_mode(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        runtime_result = application_runtime.run(fast_mode=True)
        assert runtime_result.answers == {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "zab",  # Only 'baz' has a default value, so it should be used
        }

    def test_run__is_repeatable_and_does_not_change_internal_state(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        initial_config = application_runtime.app_config.model_copy(deep=True)

        first = application_runtime.run(supplied_params={"foo": "oof"})
        second = application_runtime.run()

        # The second run is not affected by the first one's supplied params
        assert first.answers == {"foo": "oof", "bar": "BAR", "baz": "BAZ"}
        assert second.answers == {"foo": "FOO", "bar": "BAR", "baz": "BAZ"}
        # The runtime inputs are untouched by the executions
        assert application_runtime.app_config == initial_config

    def test_run__wraps_unexpected_errors_in_abort(self, application_runtime, mocker):
        original_error = ValueError("BOOM!")
        exception_logger = mocker.patch.object(application_tools.logger, "exception")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                raise original_error

        application_runtime.app_class = DummyApplication

        with pytest.raises(Abort, match="The question workflow failed to execute") as exc_info:
            application_runtime.run()

        assert exc_info.value.original_error is original_error
        assert "ValueError" in exc_info.value.subject
        assert exc_info.value.__cause__ is original_error
        exception_logger.assert_called_once_with("The question workflow failed with an unexpected runtime error")

    def test_run__inner_abort_propagates_unwrapped(self, application_runtime, mocker):
        inner_abort = Abort("Inner abort", subject="Inner subject")
        exception_logger = mocker.patch.object(application_tools.logger, "exception")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                raise inner_abort

        application_runtime.app_class = DummyApplication

        with pytest.raises(Abort) as exc_info:
            application_runtime.run()

        assert exc_info.value is inner_abort
        assert exc_info.value.subject == "Inner subject"
        exception_logger.assert_called_once_with("The question workflow aborted while executing the application")

    def test_set_name_dynamically(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                self.jobbergate_config["job_script_name"] = "very-unique-name"

        application_runtime.app_class = DummyApplication
        runtime_result = application_runtime.run()

        assert runtime_result.as_flatten_param_dict()["job_script_name"] == "very-unique-name"

    def test_set_name_dynamically__legacy(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["job_script_name"] = "very-unique-name"

        application_runtime.app_class = DummyApplication
        runtime_result = application_runtime.run()

        assert runtime_result.as_flatten_param_dict()["job_script_name"] == "very-unique-name"

    def test_choose_default_template(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                self.jobbergate_config["default_template"] = "very-unique-template"

        application_runtime.app_class = DummyApplication
        runtime_result = application_runtime.run()

        assert runtime_result.as_flatten_param_dict()["default_template"] == "very-unique-template"

    def test_choose_default_template__legacy(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["default_template"] = "very-unique-template"

        application_runtime.app_class = DummyApplication
        runtime_result = application_runtime.run()

        assert runtime_result.as_flatten_param_dict()["default_template"] == "very-unique-template"

    def test_gather_config_values__basic(self, application_runtime, dummy_render_class, mocker):
        variablename1 = "foo"
        question1 = Text(variablename1, message="gimme the foo!")

        variablename2 = "bar"
        question2 = Text(variablename2, message="gimme the bar!")

        variablename3 = "baz"
        question3 = Text(variablename3, message="gimme the baz!")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [question1, question2]

            def subflow(self, data):
                return [question3]

        application_runtime.app_class = DummyApplication
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        runtime_result = application_runtime.run()
        assert runtime_result.answers == {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }

    def test_gather_config_values__returning_none(self, application_runtime, dummy_render_class, mocker):
        """
        Test that gather_param_values raises no error when a method returns None.

        Due to differences on the implementation details, jobbergate-legacy does not raise an error in this case
        and so legacy applications expect the same from next-gen Jobbergate.
        """
        variablename1 = "foo"
        question1 = Text(variablename1, message="gimme the foo!")

        variablename2 = "bar"
        question2 = Text(variablename2, message="gimme the bar!")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [question1, question2]

            def subflow(self, data):
                return None

        application_runtime.app_class = DummyApplication
        dummy_render_class.prepared_input = {"foo": "FOO", "bar": "BAR", "baz": "BAZ"}

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        runtime_result = application_runtime.run()
        assert runtime_result.answers == {"foo": "FOO", "bar": "BAR"}

    def test_gather_config_values__fast_mode(self, application_runtime, dummy_render_class, mocker):
        variablename1 = "foo"
        question1 = Text(variablename1, message="gimme the foo!", default="oof")

        variablename2 = "bar"
        question2 = Text(variablename2, message="gimme the bar!")

        variablename3 = "baz"
        question3 = Text(variablename3, message="gimme the baz!")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [question1, question2]

            def subflow(self, data):
                return [question3]

        application_runtime.app_class = DummyApplication
        dummy_render_class.prepared_input = {"foo": "FOO", "bar": "BAR", "baz": "BAZ"}

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        runtime_result = application_runtime.run(fast_mode=True)
        assert runtime_result.answers == {"foo": "oof", "bar": "BAR", "baz": "BAZ"}

    def test_gather_config_values__skips_supplied_params(self, application_runtime, dummy_render_class, mocker):
        variablename1 = "foo"
        question1 = Text(variablename1, message="gimme the foo!", default="oof")

        variablename2 = "bar"
        question2 = Text(variablename2, message="gimme the bar!")

        variablename3 = "baz"
        question3 = Text(variablename3, message="gimme the baz!")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [question1, question2]

            def subflow(self, data):
                return [question3]

        application_runtime.app_class = DummyApplication
        dummy_render_class.prepared_input = {
            "foo": "FOO",
            "bar": "BAR",
            "baz": "BAZ",
        }

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        runtime_result = application_runtime.run(supplied_params={"bar": "rab"})
        assert runtime_result.answers == {"foo": "FOO", "bar": "rab", "baz": "BAZ"}

    def test_gather_config_values__raises_abort_if_method_not_implemented(
        self, application_runtime, dummy_render_class, mocker
    ):
        variablename1 = "foo"
        question1 = Text(variablename1, message="gimme the foo!")

        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [question1]

            def subflow(self, data):
                raise NotImplementedError("BOOM!")

        application_runtime.app_class = DummyApplication
        dummy_render_class.prepared_input = {
            "foo": "FOO",
        }

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        with pytest.raises(Abort, match="not implemented"):
            application_runtime.run()


class TestFetchApplicationRuntime:
    @pytest.fixture
    def mocked_fetch_application_data(self, dummy_application_data, mocker):
        application_response = ApplicationResponse(**dummy_application_data[0])
        return mocker.patch(
            "jobbergate_cli.subapps.applications.tools.fetch_application_data",
            return_value=application_response,
        )

    @pytest.fixture
    def get_workflow_route(self, dummy_application_data, dummy_module_source, dummy_domain, respx_mock):
        application_response = ApplicationResponse(**dummy_application_data[0])
        assert application_response.workflow_files is not None
        route = respx_mock.get(f"{dummy_domain}{application_response.workflow_files[0].path}")
        route.mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                content=dummy_module_source.encode(),
            ),
        )
        return route

    def test_success(
        self,
        mocked_fetch_application_data,
        get_workflow_route,
        dummy_context,
        dummy_module_source,
    ):
        runtime = fetch_application_runtime(dummy_context, 1)

        assert runtime.app_source_code == dummy_module_source
        assert runtime.app_data == mocked_fetch_application_data.return_value
        assert get_workflow_route.call_count == 1
        mocked_fetch_application_data.assert_called_once_with(dummy_context, 1)

    def test_caches_runtime_per_client(
        self,
        mocked_fetch_application_data,
        get_workflow_route,
        dummy_context,
    ):
        first = fetch_application_runtime(dummy_context, 1)
        second = fetch_application_runtime(dummy_context, 1)

        assert first is second
        assert get_workflow_route.call_count == 1
        assert mocked_fetch_application_data.call_count == 1

    def test_caches_runtime_under_id_and_identifier_aliases(
        self,
        mocked_fetch_application_data,
        get_workflow_route,
        dummy_context,
        dummy_application_data,
    ):
        application_response = mocked_fetch_application_data.return_value

        by_identifier = fetch_application_runtime(dummy_context, application_response.identifier)
        by_id = fetch_application_runtime(dummy_context, application_response.application_id)

        assert by_identifier is by_id
        assert get_workflow_route.call_count == 1
        assert mocked_fetch_application_data.call_count == 1

    def test_clear_cache_forces_a_new_fetch(
        self,
        mocked_fetch_application_data,
        get_workflow_route,
        dummy_context,
    ):
        first = fetch_application_runtime(dummy_context, 1)
        clear_application_runtime_cache()
        second = fetch_application_runtime(dummy_context, 1)

        assert first is not second
        assert get_workflow_route.call_count == 2

    def test_fails_when_no_workflow_file_is_available(
        self,
        mocked_fetch_application_data,
        dummy_context,
    ):
        application_response = mocked_fetch_application_data.return_value
        application_response.workflow_files = []

        with pytest.raises(
            Abort,
            match=f"Application {application_response.application_id} does not have a workflow file",
        ) as exc_info:
            fetch_application_runtime(dummy_context, 1)

        assert exc_info.value.subject == "Workflow file not found"

    def test_cached_runtime_does_not_keep_the_client_alive(
        self,
        mocked_fetch_application_data,
        get_workflow_route,
        dummy_domain,
    ):
        """
        The caches are weakly keyed by the client, so dropping the client must release the entries.

        A cached value holding a reference back to the client (e.g. through an SDK instance)
        would keep the weak key alive forever and leak every context in a long-lived process.
        """
        jg_ctx = SimpleNamespace(client=httpx.Client(base_url=dummy_domain))

        fetch_application_runtime(jg_ctx, 1)
        assert len(_application_runtime_cache._entries) == 1

        # the mock's call history holds a reference to jg_ctx (and so to the client)
        mocked_fetch_application_data.reset_mock()
        del jg_ctx
        gc.collect()

        assert len(_application_runtime_cache._entries) == 0
