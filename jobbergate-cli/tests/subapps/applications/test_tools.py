import datetime
import importlib
import pathlib

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
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import Text
from jobbergate_cli.subapps.applications.tools import (
    ApplicationRuntime,
    fetch_application_data,
    fetch_application_data_locally,
    load_application_config_from_source,
    load_application_data,
    load_application_from_source,
    load_default_config,
    save_application_files,
    upload_application,
)


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


def test_load_application_data__success(dummy_module_source, dummy_config_source):
    expected_config = load_application_config_from_source(dummy_config_source)
    application_data = ApplicationResponse(
        id=1,
        name="dummy",
        owner_email="dummy@email.com",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        template_vars=expected_config.application_config,
        workflow_files=[
            WorkflowFileResponse(
                filename="jobbergate.py",
                parent_id=1,
                runtime_config=expected_config.jobbergate_config.model_dump(),
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
            )
        ],
    )

    actual_config, app_module = load_application_data(application_data, dummy_module_source)
    assert isinstance(app_module, JobbergateApplicationBase)
    assert isinstance(actual_config, JobbergateApplicationConfig)
    assert actual_config == expected_config


def test_load_application_data__fails_if_application_module_cannot_be_loaded_from_source(dummy_config_source):
    expected_config = load_application_config_from_source(dummy_config_source)
    application_data = ApplicationResponse(
        id=1,
        name="dummy",
        owner_email="dummy@email.com",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        template_vars=expected_config.application_config,
        workflow_files=[
            WorkflowFileResponse(
                filename="jobbergate.py",
                parent_id=1,
                runtime_config=expected_config.jobbergate_config.model_dump(),
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
            )
        ],
    )

    with pytest.raises(Abort, match="The application source fetched from the API is not valid"):
        load_application_data(application_data, "Not Python at all")


def test_load_application_data__fails_if_application_config_is_not_valid_YAML(
    dummy_module_source,
    dummy_config_source,
):
    expected_config = load_application_config_from_source(dummy_config_source)
    application_data = ApplicationResponse(
        id=1,
        name="dummy",
        owner_email="dummy@email.com",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        template_vars=expected_config.application_config,
        workflow_files=[],
    )

    with pytest.raises(Abort, match="No workflow file found in application data"):
        load_application_data(application_data, dummy_module_source)


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


def test_load_application_from_source__success(dummy_module_source, dummy_jobbergate_application_config):
    application = load_application_from_source(dummy_module_source, dummy_jobbergate_application_config)
    assert isinstance(application, JobbergateApplicationBase)
    assert application.mainflow
    assert application.jobbergate_config == dict(
        default_template="job-script-template.py.j2",
        template_files=[pathlib.Path("job-script-template.py.j2")],
        supporting_files=None,
        supporting_files_output_name=None,
        user_supplied_key="user-supplied-value",
    )
    assert application.application_config == dict(
        foo="foo",
        bar="bar",
        baz="baz",
    )


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
        actual_result = application_runtime.as_flatten_param_dict()
        expected_result = {
            "template_files": None,
            "supporting_files_output_name": None,
            "supporting_files": None,
            "default_template": "test-job-script.py.j2",
        }

        assert actual_result == expected_result

    def test_execute_application__basic(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        application_runtime.execute_application()
        assert application_runtime.answers == dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )

    def test_execute_application__with_supplied_params(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        application_runtime.supplied_params = dict(foo="oof")
        application_runtime.execute_application()
        assert application_runtime.answers == dict(
            foo="oof",
            bar="BAR",
            baz="BAZ",
        )

    def test_execute_application__with_fast_mode(
        self,
        application_runtime,
        dummy_render_class,
        mocker,
    ):
        dummy_render_class.prepared_input = dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )
        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)

        application_runtime.fast_mode = True

        application_runtime.execute_application()
        assert application_runtime.answers == dict(
            foo="FOO",
            bar="BAR",
            baz="zab",  # Only 'baz' has a default value, so it should be used
        )

    def test_set_name_dynamically(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                self.jobbergate_config["job_script_name"] = "very-unique-name"

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.execute_application()

        assert application_runtime.as_flatten_param_dict()["job_script_name"] == "very-unique-name"

    def test_set_name_dynamically__legacy(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["job_script_name"] = "very-unique-name"

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.execute_application()

        assert application_runtime.as_flatten_param_dict()["job_script_name"] == "very-unique-name"

    def test_choose_default_template(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                self.jobbergate_config["default_template"] = "very-unique-template"

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.execute_application()

        assert application_runtime.as_flatten_param_dict()["default_template"] == "very-unique-template"

    def test_choose_default_template__legacy(self, application_runtime):
        class DummyApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                data["default_template"] = "very-unique-template"

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.execute_application()

        assert application_runtime.as_flatten_param_dict()["default_template"] == "very-unique-template"

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

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        dummy_render_class.prepared_input = dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        application_runtime._gather_answers()
        assert application_runtime.answers == dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )

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

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        dummy_render_class.prepared_input = dict(foo="FOO", bar="BAR", baz="BAZ")

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        application_runtime._gather_answers()
        assert application_runtime.answers == dict(foo="FOO", bar="BAR")

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

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.fast_mode = True
        dummy_render_class.prepared_input = dict(foo="FOO", bar="BAR", baz="BAZ")

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        application_runtime._gather_answers()
        assert application_runtime.answers == dict(foo="oof", bar="BAR", baz="BAZ")

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

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        application_runtime.supplied_params = dict(bar="rab")
        dummy_render_class.prepared_input = dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        application_runtime._gather_answers()
        assert application_runtime.answers == dict(foo="FOO", bar="rab", baz="BAZ")

    def test_gather_config_values__raises_Abort_if_method_not_implemented(
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

        application_runtime.app_module = DummyApplication(application_runtime.app_config.model_dump())
        dummy_render_class.prepared_input = dict(
            foo="FOO",
        )

        mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
        with pytest.raises(Abort, match="not implemented"):
            application_runtime._gather_answers()
