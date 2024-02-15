import importlib
import json
import pathlib
from textwrap import dedent
from unittest import mock

import httpx
import pytest
import respx

from jobbergate_cli.exceptions import Abort, JobbergateCliError
from jobbergate_cli.schemas import ApplicationResponse, JobScriptResponse
from jobbergate_cli.subapps.job_scripts.tools import (
    JobbergateConfig,
    download_job_script_files,
    fetch_job_script_data,
    flatten_param_dict,
    get_template_output_name_mapping,
    inject_sbatch_params,
    question_helper,
    remove_prefix_suffix,
    render_job_script,
    render_job_script_locally,
    render_template,
    upload_job_script_files,
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


def test_inject_sbatch_params():
    sbatch_params = ["--comment=some_comment", "--nice=-1", "-N 10"]

    job_script_data_as_string = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    expected_result = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out

        # Sbatch params injected at rendering time
        #SBATCH --comment=some_comment
        #SBATCH --nice=-1
        #SBATCH -N 10

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert actual_result == expected_result


def test_inject_sbatch_params__no_sbatch_flag():
    sbatch_params = ["--comment=some_comment", "--nice=-1", "-N 10"]

    job_script_data_as_string = dedent(
        """
        #!/bin/bash

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    expected_result = dedent(
        """
        #!/bin/bash

        # Sbatch params injected at rendering time
        #SBATCH --comment=some_comment
        #SBATCH --nice=-1
        #SBATCH -N 10

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert actual_result == expected_result


def test_render_template__success(tmp_path):
    template_path = tmp_path / "dummy.j2"
    template_path.write_text("{{ foo }} {{ bar }} {{ baz }}")

    parameters = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    expected_output = "FOO BAR BAZ"

    assert render_template(template_path, parameters) == expected_output


def test_render_template__fails_if_template_does_not_exist(tmp_path):
    non_exist = tmp_path / "does/not/exist"
    with pytest.raises(Abort, match=f"Template file {non_exist} does not exist"):
        render_template(non_exist, {})


def test_render_template__fails_if_template_is_invalid(tmp_path):
    invalid_template = tmp_path / "invalid.j2"
    invalid_template.write_text("{{ foo")

    with pytest.raises(Abort, match=f"Unable to process jinja template filename={invalid_template}"):
        render_template(invalid_template, {})


def test_render_job_script_locally__success(
    dummy_context,
    dummy_application_dir,
    dummy_render_class,
    tmp_path,
    mocker,
):
    expected_template_data = dedent(
        """
        #!/bin/python3

        #SBATCH -J dummy_job
        #SBATCH -t 60
        print("I am a very, very dumb job script")
        print(f"foo='FOO'")
        print(f"bar='BAR'")
        print(f"baz='BAZ'")
        """
    )
    mocker.patch("jobbergate_cli.subapps.job_scripts.tools.render_template", return_value=expected_template_data)

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )
    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )

    write_mock = mocker.patch("builtins.open", mocker.mock_open())

    render_job_script_locally(dummy_context, "dummy-job-script", dummy_application_dir, tmp_path, fast=True)

    write_mock().write.assert_called_once_with(expected_template_data)


def test_render_job_script__providing_a_name(
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
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.application_id}"
    )
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = render_job_script(
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


def test_render_job_script__set_name_dynamically_from_application_config(
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
    Test that we can create a job script by setting its name at runtime.
    """
    attach_persona("dummy@dummy.com")

    new_name = "new-name"

    application_response = ApplicationResponse(**dummy_application_data[0])
    application_response.template_vars["job_script_name"] = new_name

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
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.application_id}"
    )
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = render_job_script(
        dummy_context,
        name=new_name,
        application_id=1,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=1,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse.parse_obj(desired_job_script_data)


def test_render_job_script__set_name_dynamically_from_jobbergate_config(
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
    Test that we can create a job script by setting its name at runtime.
    """
    attach_persona("dummy@dummy.com")

    new_name = "new-name"

    application_response = ApplicationResponse(**dummy_application_data[0])
    application_response.workflow_files[0].runtime_config["job_script_name"] = new_name

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
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.application_id}"
    )
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = render_job_script(
        dummy_context,
        name=new_name,
        application_id=1,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=1,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse.parse_obj(desired_job_script_data)


def test_render_job_script__without_a_name(
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
        f"{dummy_domain}/jobbergate/job-scripts/render-from-template/{application_response.application_id}"
    )
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=desired_job_script_data,
        ),
    )

    actual_job_script_data = render_job_script(
        dummy_context,
        name=None,
        application_id=application_response.application_id,
        fast=True,
    )

    mocked_fetch_application_data.assert_called_once_with(
        dummy_context,
        id=application_response.application_id,
        identifier=None,
    )

    assert actual_job_script_data == JobScriptResponse.parse_obj(desired_job_script_data)


def test_question_helper__return_actual_value_when_actual_value_is_not_none():
    question_func = mock.Mock()

    assert (
        question_helper(
            question_func=question_func,
            text="Give me foo",
            default="foo",
            fast=True,
            actual_value="bar",
        )
        == "bar"
    )

    assert question_func.call_count == 0

    assert (
        question_helper(
            question_func=question_func,
            text="Give me foo",
            default="foo",
            fast=False,
            actual_value="bar",
        )
        == "bar"
    )

    assert question_func.call_count == 0


def test_question_helper__return_default_when_actual_value_is_none_on_fast_mode():
    question_func = mock.Mock()

    assert (
        question_helper(
            question_func=question_func,
            text="Give me foo",
            default="foo",
            fast=True,
            actual_value=None,
        )
        == "foo"
    )

    assert question_func.call_count == 0


def test_question_helper__ask_question_when_actual_value_is_none_on_non_fast_mode():
    question_func = mock.Mock()

    question_helper(
        question_func=question_func,
        text="Give me foo",
        default="foo",
        fast=False,
        actual_value=None,
    )

    question_func.assert_called_once_with("Give me foo", default="foo")


class TestDownloadJobScriptFiles:
    """
    Test the save_job_script_files function.
    """

    def test_download_job_scripts_files__all_files(
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
        job_script_id = 1
        respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/{job_script_id}").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dummy_job_script_data[0],
            ),
        )
        job_script_data = JobScriptResponse.parse_obj(dummy_job_script_data[0])

        get_file_routes = [respx_mock.get(f"{dummy_domain}{f.path}") for f in job_script_data.files]
        for route in get_file_routes:
            route.mock(
                return_value=httpx.Response(
                    httpx.codes.OK,
                    content=dummy_template_source.encode(),
                ),
            )

        list_of_files = [tmp_path / f.filename for f in job_script_data.files]

        assert len(list_of_files) >= 1, "sanity check"

        files = download_job_script_files(job_script_id, dummy_context, tmp_path)

        assert files == job_script_data.files
        assert set(tmp_path.rglob("*")) == set(list_of_files)
        assert all(r.called for r in get_file_routes)

        assert all(p.read_text() == dummy_template_source for p in list_of_files)


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

        assert get_template_output_name_mapping(config, "dummy-name") == expected_mapping

    def test_default_template_valid_output_name__legacy_mode(self, tweak_settings):
        config = JobbergateConfig(
            default_template="templates/template.j2",
            output_directory=pathlib.Path("."),
            supporting_files=None,
            supporting_files_output_name=None,
        )
        expected_mapping = {"template.j2": "dummy-name.job"}

        with tweak_settings(JOBBERGATE_LEGACY_NAME_CONVENTION=True):
            assert get_template_output_name_mapping(config, "dummy-name") == expected_mapping

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

        assert get_template_output_name_mapping(config, "dummy-name") == expected_mapping

    def test_default_template_not_specified(self):
        config = JobbergateConfig(
            template_files=[],
            output_directory=pathlib.Path("."),
            supporting_files_output_name=None,
            supporting_files=None,
        )
        with pytest.raises(Abort, match="Default template was not specified"):
            get_template_output_name_mapping(config, "dummy-name")

    def test_supporting_files_output_names_multiple_values(self):
        config = JobbergateConfig(
            default_template="templates/template1.j2",
            supporting_files_output_name={
                "template2.j2": ["output3", "output4"],
            },
        )

        with pytest.raises(Abort, match="template='template2.j2' has 2 output names"):
            get_template_output_name_mapping(config, "dummy-name")


class TestUploadJobScriptFiles:
    """Test the upload_job_script_files function."""

    job_script_id = 1

    @pytest.fixture(scope="function")
    def mocked_routes(self, dummy_domain):
        def _helper(assert_all_mocked=True, assert_all_called=False):
            app_mock = respx.mock(
                base_url=dummy_domain,
                assert_all_mocked=assert_all_mocked,
                assert_all_called=assert_all_called,
            )

            app_mock.put(
                path=f"/jobbergate/job-scripts/{self.job_script_id}/upload/ENTRYPOINT",
                name="upload_entrypoint",
            ).respond(httpx.codes.OK)

            app_mock.put(
                path=f"/jobbergate/job-scripts/{self.job_script_id}/upload/SUPPORT",
                name="upload_support",
            ).respond(httpx.codes.OK)
            return app_mock

        return _helper

    def test_upload_job_script__success(
        self,
        dummy_context,
        mocked_routes,
        tmp_path,
    ):
        with mocked_routes(assert_all_called=True) as routes:
            dummy_job_script = tmp_path / "dummy.sh"
            dummy_job_script.write_text("echo hello world")

            dummy_support_1 = tmp_path / "dummy-support-1.txt"
            dummy_support_1.write_text("dummy 1")

            dummy_support_2 = tmp_path / "dummy-support-2.txt"
            dummy_support_2.write_text("dummy 2")

            upload_job_script_files(
                dummy_context, self.job_script_id, dummy_job_script, [dummy_support_1, dummy_support_2]
            )

            assert routes["upload_entrypoint"].call_count == 1
            assert b'filename="dummy.sh"' in routes["upload_entrypoint"].calls[0].request.content
            assert b"echo hello world" in routes["upload_entrypoint"].calls[0].request.content

            assert routes["upload_support"].call_count == 2

            assert b'filename="dummy-support-1.txt"' in routes["upload_support"].calls[0].request.content
            assert b"dummy 1" in routes["upload_support"].calls[0].request.content

            assert b'filename="dummy-support-2.txt"' in routes["upload_support"].calls[1].request.content
            assert b"dummy 2" in routes["upload_support"].calls[1].request.content

    def test_upload_job_script__raises_exception_if_context_client_is_undefined(
        self,
        dummy_context,
        tmp_path,
    ):
        dummy_job_script = tmp_path / "dummy.sh"
        dummy_job_script.write_text("echo hello world")

        dummy_context.client = None
        with pytest.raises(JobbergateCliError, match="not defined"):
            upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script)

    def test_upload_job_script__raises_exception_if_job_script_does_not_exist_or_is_not_a_file(
        self,
        dummy_context,
        tmp_path,
    ):
        dummy_job_script = tmp_path / "dummy.sh"

        with pytest.raises(Abort, match="Job Script file .* does not exist"):
            upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script)

        dummy_job_script.mkdir()
        with pytest.raises(Abort, match="Job Script file .* is not a file"):
            upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script)

    def test_upload_job_script__raises_exception_if_job_supporting_file_does_not_exist_or_is_not_a_file(
        self,
        dummy_context,
        tmp_path,
    ):
        dummy_job_script = tmp_path / "dummy.sh"
        dummy_job_script.touch()

        dummy_support_1 = tmp_path / "dummy-support-1.txt"

        with pytest.raises(Abort, match="Supporting file .* does not exist"):
            upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script, [dummy_support_1])

        dummy_support_1.mkdir()
        with pytest.raises(Abort, match="Supporting file .* is not a file"):
            upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script, [dummy_support_1])

    def test_upload_job_script__raises_exception_if_job_script_fails_to_upload(
        self,
        dummy_context,
        mocked_routes,
        tmp_path,
    ):
        with mocked_routes() as routes:
            dummy_job_script = tmp_path / "dummy.sh"
            dummy_job_script.write_text("echo hello world")
            routes["upload_entrypoint"].respond(httpx.codes.BAD_REQUEST)

            with pytest.raises(Abort, match="Job Script file .* failed to upload"):
                upload_job_script_files(dummy_context, self.job_script_id, dummy_job_script)

            assert routes["upload_entrypoint"].call_count == 1
            assert b'filename="dummy.sh"' in routes["upload_entrypoint"].calls[0].request.content

    def test_upload_job_script__raises_exception_if_any_of_the_supporting_files_fail_to_upload(
        self,
        dummy_context,
        mocked_routes,
        tmp_path,
    ):
        with mocked_routes(assert_all_called=True) as routes:
            routes["upload_support"].respond(httpx.codes.BAD_REQUEST)

            dummy_job_script = tmp_path / "dummy.sh"
            dummy_job_script.write_text("echo hello world")

            dummy_support_1 = tmp_path / "dummy-support-1.txt"
            dummy_support_1.write_text("dummy 1")

            dummy_support_2 = tmp_path / "dummy-support-2.txt"
            dummy_support_2.write_text("dummy 2")

            with pytest.raises(JobbergateCliError, match="Supporting file .* was not accepted"):
                upload_job_script_files(
                    dummy_context, self.job_script_id, dummy_job_script, [dummy_support_1, dummy_support_2]
                )

            assert routes["upload_entrypoint"].call_count == 1
            assert b'filename="dummy.sh"' in routes["upload_entrypoint"].calls[0].request.content

            assert routes["upload_support"].call_count == 2
            assert b'filename="dummy-support-1.txt"' in routes["upload_support"].calls[0].request.content
            assert b'filename="dummy-support-2.txt"' in routes["upload_support"].calls[1].request.content
