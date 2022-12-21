import importlib
import pathlib

import httpx
import pytest

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ApplicationResponse, JobbergateApplicationConfig
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.tools import (
    execute_application,
    fetch_application_data,
    get_upload_files,
    load_application_data,
    load_application_from_source,
    load_default_config,
    save_application_files,
)
from jobbergate_cli.text_tools import dedent


def test_get_upload_files__fails_if_application_directory_does_not_exist(tmp_path):
    application_path = tmp_path / "dummy"

    with pytest.raises(
        Abort,
        match=f"Application directory {application_path} does not exist",
    ):
        with get_upload_files(application_path):
            pass


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
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/applications/{app_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, id=app_id)
    assert fetch_route.called
    assert result == ApplicationResponse(**app_data)


def test_fetch_application_data__success__using_identifier(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    app_data = dummy_application_data[0]
    app_identifier = app_data["application_identifier"]
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/applications/{app_identifier}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, identifier=app_identifier)
    assert fetch_route.called
    assert result == ApplicationResponse(**app_data)


def test_fetch_application_data__fails_with_both_id_or_identifier(dummy_context):
    with pytest.raises(Abort, match="You may not supply both"):
        fetch_application_data(dummy_context, id=1, identifier="one")


def test_fetch_application_data__fails_with_neither_id_or_identifier(dummy_context):
    with pytest.raises(Abort, match="You must supply either"):
        fetch_application_data(dummy_context)


def test_load_application_data__success(dummy_module_source, dummy_config_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_source_file=dummy_module_source,
        application_config=dummy_config_source,
    )
    (app_config, app_module) = load_application_data(app_data)
    assert isinstance(app_module, JobbergateApplicationBase)
    assert isinstance(app_config, JobbergateApplicationConfig)


def test_load_application_data__fails_if_application_module_cannot_be_loaded_from_source(dummy_config_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_source_file="Not python at all",
        application_config=dummy_config_source,
    )

    with pytest.raises(Abort, match="The application source fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_data__fails_if_application_config_is_not_valid_YAML(dummy_module_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_source_file=dummy_module_source,
        application_config=":",
    )

    with pytest.raises(Abort, match="The application config fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_data__fails_if_application_config_is_not_valid_JobbergateApplicationConfig(
    dummy_module_source,
):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_file=dummy_module_source,
        application_config=dedent(
            """
            foo: bar
            """
        ),
    )

    with pytest.raises(Abort, match="The application config fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_from_source__success(dummy_module_source, dummy_jobbergate_application_config):
    application = load_application_from_source(dummy_module_source, dummy_jobbergate_application_config)
    assert isinstance(application, JobbergateApplicationBase)
    assert application.mainflow
    assert application.jobbergate_config == dict(
        default_template="test-job-script.py.j2",
        template_files=[pathlib.Path("test-job-script.py.j2")],
        output_directory=pathlib.Path("."),
        supporting_files=None,
        supporting_files_output_name=None,
        job_script_name=None,
        user_supplied_key="user-supplied-value",
    )
    assert application.application_config == dict(
        foo="foo",
        bar="bar",
        baz="baz",
    )


def test_execute_application__basic(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
    )
    assert app_params == dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )


def test_execute_application__with_supplied_params(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
        supplied_params=dict(foo="oof"),
    )
    assert app_params == dict(
        foo="oof",
        bar="BAR",
        baz="BAZ",
    )


def test_execute_application__with_fast_mode(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
        fast_mode=True,
    )
    assert app_params == dict(
        foo="FOO",
        bar="BAR",
        baz="zab",  # Only 'baz' has a default value, so it should be used
    )


class TestDownloadApplicationFiles:
    """
    Test the save_application_files function.
    """

    def test_save_application_files__no_files(self, tmp_path):
        """
        Test that the function returns an empty list if there are no files to download.
        """
        application_data = ApplicationResponse(
            id=1,
            application_name="dummy",
            application_owner_email="dummy@email.com",
            application_uploaded=True,
        )

        desired_list_of_files = []

        assert save_application_files(application_data, tmp_path) == desired_list_of_files
        assert list(tmp_path.rglob("*")) == desired_list_of_files

    def test_save_application_files__all_files(
        self,
        tmp_path,
        dummy_module_source,
        dummy_config_source,
        dummy_template_source,
    ):
        """
        Test that the function downloads all files.
        """
        application_data = ApplicationResponse(
            id=13,
            application_name="dummy",
            application_owner_email="dummy@dummy.org",
            application_uploaded=True,
            application_source_file=dummy_module_source,
            application_config=dummy_config_source,
            application_templates={"test-job-script.py.j2": dummy_template_source},
        )

        desired_list_of_files = [
            tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
            tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
            tmp_path / "templates" / "test-job-script.py.j2",
        ]

        assert save_application_files(application_data, tmp_path) == desired_list_of_files
        assert set(tmp_path.rglob("*")) == {tmp_path / "templates", *desired_list_of_files}

        assert (tmp_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME).read_text() == dummy_config_source
        assert (tmp_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME).read_text() == dummy_module_source
        assert (tmp_path / "templates" / "test-job-script.py.j2").read_text() == dummy_template_source
