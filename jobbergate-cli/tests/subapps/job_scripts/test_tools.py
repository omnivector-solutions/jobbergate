import importlib
import json
import pathlib

import httpx
import pytest
from pydantic import ValidationError

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ApplicationResponse, JobScriptResponse
from jobbergate_cli.subapps.job_scripts.tools import (
    change_archive_status,
    create_job_script,
    fetch_job_script_data,
    save_job_script_files,
    validate_parameter_file,
)


def test_validate_parameter_file__success(tmp_path):
    parameter_path = tmp_path / "dummy.json"
    dummy_data = dict(
        foo="one",
        bar=2,
        baz=False,
    )
    parameter_path.write_text(json.dumps(dummy_data))
    assert validate_parameter_file(parameter_path) == dummy_data


def test_validate_parameter_file__fails_if_file_does_not_exist():
    with pytest.raises(Abort, match="does not exist"):
        validate_parameter_file(pathlib.Path("some/fake/path"))


def test_validate_parameter_file__fails_if_file_is_not_valid_json(tmp_path):
    parameter_path = tmp_path / "dummy.json"
    parameter_path.write_text("clearly not json")
    with pytest.raises(Abort, match="is not valid JSON"):
        validate_parameter_file(parameter_path)


def test_fetch_job_script_data__success(
    respx_mock,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_script_data[0],
        ),
    )
    job_script = fetch_job_script_data(dummy_context, 1)
    assert job_script == JobScriptResponse(**dummy_job_script_data[0])


def test_create_job_script__providing_a_name(
    dummy_application_data,
    dummy_job_script_data,
    dummy_domain,
    dummy_context,
    dummy_render_class,
    attach_persona,
    respx_mock,
    mocker,
):
    """
    Test that we can create a job script with the desired name.
    """
    attach_persona("dummy@dummy.com")

    application_response = ApplicationResponse(**dummy_application_data[0])
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.tools.fetch_application_data",
        return_value=application_response,
    )

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    desired_job_script_data = dummy_job_script_data[0]
    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )
    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = create_job_script(
        dummy_context,
        name=desired_job_script_data["job_script_name"],
        application_id=1,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=1,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse(**desired_job_script_data)


def test_create_job_script__without_a_name(
    dummy_application_data,
    dummy_job_script_data,
    dummy_domain,
    dummy_context,
    dummy_render_class,
    attach_persona,
    respx_mock,
    mocker,
):
    """
    Test that we can create a job script without providing a name.

    In this case, it should be created with the name of the base application.
    """
    attach_persona("dummy@dummy.com")

    application_response = ApplicationResponse(**dummy_application_data[0])
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.tools.fetch_application_data",
        return_value=application_response,
    )

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    desired_job_script_data = dummy_job_script_data[0]
    desired_job_script_data["name"] = application_response.application_name

    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )
    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = create_job_script(
        dummy_context,
        name=None,
        application_id=application_response.id,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=application_response.id,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse(**desired_job_script_data)


class TestSaveJobScriptFiles:
    """
    Test the save_job_script_files function.
    """

    def test_save_job_scripts_files__no_files(self, dummy_job_script_data):
        """
        Base test for the save_job_script_files function.

        job_script_files is a required field on JobScriptResponse, so job script files are always present.
        """
        job_script_data = dummy_job_script_data[0].copy()
        job_script_data.pop("job_script_files")

        with pytest.raises(ValidationError):
            JobScriptResponse(**job_script_data)

    def test_save_job_scripts_files__all_files(
        self,
        tmp_path,
        dummy_job_script_data,
        dummy_template_source,
    ):
        """
        Test that we can download all the files from a job script.
        """
        job_script_data = JobScriptResponse(**dummy_job_script_data[0])

        desired_list_of_files = [tmp_path / "application.sh"]
        actual_list_of_files = save_job_script_files(job_script_data, tmp_path)

        assert actual_list_of_files == desired_list_of_files
        assert set(tmp_path.rglob("*")) == set(desired_list_of_files)

        assert (tmp_path / "application.sh").read_text() == dummy_template_source


def test_change_archive_status__success__archive(
    respx_mock,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
):
    """
    Test that the change_archive_status() method sends an update request that archives the job_script.

    Verifies that the request body only includes the is_archived parameter set to True.
    """
    js_data = dummy_job_script_data[0]
    js_id = js_data["id"]
    archive_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-scripts/{js_id}")

    change_archive_status(dummy_context, js_id, True)
    assert archive_route.called
    assert json.loads(archive_route.calls.last.request.content) == dict(is_archived=True)


def test_change_archive_status__success__restore(
    respx_mock,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
):
    """
    Test that the change_archive_status() method sends an update request that restores the job_script.

    Verifies that the request body only includes the is_archived parameter set to False.
    """
    js_data = dummy_job_script_data[0]
    js_id = js_data["id"]
    archive_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-scripts/{js_id}")

    change_archive_status(dummy_context, js_id, False)
    assert archive_route.called
    assert json.loads(archive_route.calls.last.request.content) == dict(is_archived=False)
