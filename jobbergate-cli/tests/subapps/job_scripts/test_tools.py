import importlib
import json
import pathlib

import httpx
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ApplicationResponse, JobScriptResponse
from jobbergate_cli.subapps.job_scripts.tools import (
    JobbergateConfig,
    create_job_script,
    fetch_job_script_data,
    flatten_param_dict,
    get_template_output_name_mapping,
    remove_prefix_suffix,
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
    assert job_script == JobScriptResponse.parse_obj(dummy_job_script_data[0])


def test_create_job_script__providing_a_name(
    dummy_application_data,
    dummy_job_script_data,
    dummy_module_source,
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
    assert application_response.workflow_files is not None
    get_workflow_route = respx_mock.get(f"{dummy_domain}{application_response.workflow_files[0].path}")
    get_workflow_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            content=dummy_module_source.encode(),
        ),
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
    create_route = respx_mock.post(
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.id}"
    )
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = create_job_script(
        dummy_context,
        name=desired_job_script_data["name"],
        application_id=1,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=1,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse.parse_obj(desired_job_script_data)


def test_create_job_script__without_a_name(
    dummy_application_data,
    dummy_job_script_data,
    dummy_module_source,
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
    assert application_response.workflow_files is not None
    get_workflow_route = respx_mock.get(f"{dummy_domain}{application_response.workflow_files[0].path}")
    get_workflow_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            content=dummy_module_source.encode(),
        ),
    )

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    desired_job_script_data = dummy_job_script_data[0]
    desired_job_script_data["name"] = application_response.name

    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )
    create_route = respx_mock.post(
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.id}"
    )
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

    assert actual_job_script_data == JobScriptResponse.parse_obj(desired_job_script_data)


class TestSaveJobScriptFiles:
    """
    Test the save_job_script_files function.
    """

    def test_save_job_scripts_files__all_files(
        self,
        tmp_path,
        respx_mock,
        dummy_context,
        dummy_domain,
        dummy_job_script_data,
        dummy_template_source,
    ):
        """
        Test that we can download all the files from a job script.
        """
        job_script_data = JobScriptResponse.parse_obj(dummy_job_script_data[0])

        get_file_routes = [respx_mock.get(f"{dummy_domain}{f.path}") for f in job_script_data.files]
        for route in get_file_routes:
            route.mock(
                return_value=httpx.Response(
                    httpx.codes.OK,
                    content=dummy_template_source.encode(),
                ),
            )
        desired_list_of_files = [tmp_path / f.filename for f in job_script_data.files]

        assert len(desired_list_of_files) >= 1

        actual_list_of_files = save_job_script_files(dummy_context, job_script_data, tmp_path)

        assert actual_list_of_files == desired_list_of_files
        assert set(tmp_path.rglob("*")) == set(desired_list_of_files)
        assert all(r.called for r in get_file_routes)

        assert all(p.read_text() == dummy_template_source for p in actual_list_of_files)


def test_flatten_param_dict__success():
    param_dict = {
        "application_config": {"job_name": "rats", "partitions": ["foo", "bar"]},
        "jobbergate_config": {
            "default_template": "test_job_script.sh.j2",
            "supporting_files": ["support-1.j2", "support-2.j2"],
            "supporting_files_output_name": {"support-1.j2": "support-10", "support-2.j2": "support-20"},
            "template_files": ["test_job_script.sh.j2", "support-1.j2", "support-2.j2"],
            "job_script_name": None,
            "output_directory": ".",
            "partition": "debug",
            "job_name": "rats",
        },
    }
    actual_result = flatten_param_dict(param_dict)
    expected_result = {
        "default_template": "test_job_script.sh.j2",
        "job_name": "rats",
        "job_script_name": None,
        "output_directory": ".",
        "partition": "debug",
        "partitions": ["foo", "bar"],
        "supporting_files": ["support-1.j2", "support-2.j2"],
        "supporting_files_output_name": {"support-1.j2": "support-10", "support-2.j2": "support-20"},
        "template_files": ["test_job_script.sh.j2", "support-1.j2", "support-2.j2"],
    }

    assert actual_result == expected_result


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        ("templates/test.sh.j2", "test.sh"),
        ("path/to/file.py.j2", "path/to/file.py"),
        ("templates/file.py.jinja2", "file.py"),
        ("templates/test.sh.jinja2", "test.sh"),
        ("other/path/test.py", "other/path/test.py"),
    ],
)
def test_remove_prefix_suffix(input_string, expected_output):
    assert remove_prefix_suffix(input_string) == expected_output


class TestGetTemplateOutputNameMapping:
    """Test the get_template_output_name_mapping function."""

    def test_default_template_valid_output_name(self):
        config = JobbergateConfig(
            default_template="templates/template.j2",
            output_directory=pathlib.Path("."),
            supporting_files=None,
            supporting_files_output_name=None,
        )
        expected_mapping = {"template.j2": "template"}

        assert get_template_output_name_mapping(config) == expected_mapping

    def test_supporting_files_with_valid_output_names(self):
        config = JobbergateConfig(
            template_files=[pathlib.Path("templates/template1.j2"), pathlib.Path("templates/template2.j2")],
            default_template="templates/template1.j2",
            output_directory=pathlib.Path("."),
            supporting_files=["templates/support1.j2", "templates/support2.j2"],
            supporting_files_output_name={
                "templates/support1.j2": ["output1.txt"],
                "templates/support2.j2": ["output2.txt"],
            },
        )

        expected_mapping = {"template1.j2": "template1", "support1.j2": "output1.txt", "support2.j2": "output2.txt"}

        assert get_template_output_name_mapping(config) == expected_mapping

    def test_default_template_not_specified(self):
        config = JobbergateConfig(
            template_files=[],
            output_directory=pathlib.Path("."),
            supporting_files_output_name=None,
            supporting_files=None,
        )
        with pytest.raises(Abort, match="Default template was not specified"):
            get_template_output_name_mapping(config)

    def test_supporting_files_output_names_multiple_values(self):
        config = JobbergateConfig(
            default_template="templates/template1.j2",
            supporting_files_output_name={
                "template2.j2": ["output3", "output4"],
            },
        )

        with pytest.raises(Abort, match="template='template2.j2' has 2 output names"):
            get_template_output_name_mapping(config)
