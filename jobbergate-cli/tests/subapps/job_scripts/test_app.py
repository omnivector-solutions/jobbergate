import importlib
import json
import shlex
from unittest import mock

import httpx
import pytest

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.schemas import (
    ApplicationResponse,
    JobScriptResponse,
    JobSubmissionResponse,
    ListResponseEnvelope,
    Pagination,
)
from jobbergate_cli.subapps.job_scripts.app import (
    HIDDEN_FIELDS,
    JOB_SUBMISSION_HIDDEN_FIELDS,
    create,
    delete,
    download_files,
    get_one,
    list_all,
    pathlib,
    show_files,
    style_mapper,
    update,
)
from jobbergate_cli.text_tools import unwrap


def test_list_all__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts?all=false").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_script_data,
                pagination=dict(
                    total=3,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_job_script_data,
            pagination=Pagination(total=3, start=None, limit=None),
        ),
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


def test_list_all__search_makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts?all=false&search=script1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=[dummy_job_script_data[0]],
                pagination=dict(
                    total=1,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results")
    result = cli_runner.invoke(test_app, shlex.split("list-all --search script1"))
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=[dummy_job_script_data[0]],
            pagination=Pagination(total=1, start=None, limit=None),
        ),
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )
    assert dummy_job_script_data[0]["id"] == 1, f"list-all searched item failed "


def test_list_all__sort_order_makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data_reversed,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts?all=false&sort_ascending=false&sort_field=id").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_script_data_reversed,
                pagination=dict(
                    total=3,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results")
    result = cli_runner.invoke(test_app, shlex.split(f"list-all --sort-order {SortOrder.DESCENDING} --sort-field id"))
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_job_script_data_reversed,
            pagination=Pagination(total=3, start=None, limit=None),
        ),
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )
    assert dummy_job_script_data_reversed[0]["id"] == 3, f"list-all List item order failed "
    assert dummy_job_script_data_reversed[2]["id"] == 1, f"list-all List item order failed "


def test_list_all__from_application_id_makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts?all=false&from_application_id=1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_script_data,
                pagination=dict(
                    total=3,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results")
    result = cli_runner.invoke(test_app, shlex.split("list-all --from-application-id 1"))
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_job_script_data,
            pagination=Pagination(total=3, start=None, limit=None),
        ),
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_script_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split("get-one --id=1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        JobScriptResponse(**dummy_job_script_data[0]),
        title="Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_create__non_fast_mode_and_job_submission(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_job_script_data,
    dummy_job_submission_data,
    dummy_domain,
    dummy_render_class,
    cli_runner,
    tmp_path,
    attach_persona,
    mocker,
):
    application_response = ApplicationResponse(**dummy_application_data[0])

    job_script_data = dummy_job_script_data[0]
    job_script_id = job_script_data["id"]

    job_submission_data = dummy_job_submission_data[0]

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_script_data,
        ),
    )

    sbatch_params = " ".join(f"--sbatch-params={i}" for i in (1, 2, 3))

    param_file_path = tmp_path / "param_file.json"
    param_file_path.write_text(json.dumps(dict(foo="oof")))

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    attach_persona("dummy@dummy.com")

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.tools.fetch_application_data",
        return_value=application_response,
    )
    mocked_create_job_submission = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.app.create_job_submission",
        return_value=JobSubmissionResponse(**job_submission_data),
    )
    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                create --name=dummy-name
                       --application-id={application_response.id}
                       --param-file={param_file_path}
                       {sbatch_params}
                """
            )
        ),
        input="y\n",  # To confirm that the job should be submitted right away
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert mocked_fetch_application_data.called_once_with(
        dummy_context,
        id=application_response.id,
        identifier=None,
    )
    assert mocked_create_job_submission.called_once_with(
        dummy_context,
        job_script_id,
        "dummy-name",
    )
    assert create_route.called
    content = json.loads(create_route.calls.last.request.content)
    assert content == dict(
        param_dict=dict(
            application_config=dict(
                foo="oof",
                bar="BAR",
                baz="BAZ",
            ),
            jobbergate_config=dict(
                default_template="test-job-script.py.j2",
                job_script_name=None,
                output_directory=".",
                supporting_files=None,
                supporting_files_output_name=None,
                template_files=["test-job-script.py.j2"],
                user_supplied_key="user-supplied-value",
            ),
        ),
        application_id=application_response.id,
        job_script_name="dummy-name",
        job_script_description=None,
        sbatch_params=["1", "2", "3"],
    )

    mocked_render.assert_has_calls(
        [
            mocker.call(
                dummy_context,
                JobScriptResponse(**job_script_data),
                title="Created Job Script",
                hidden_fields=HIDDEN_FIELDS,
            ),
            mocker.call(
                dummy_context,
                JobSubmissionResponse(**job_submission_data),
                title="Created Job Submission (Fast Mode)",
                hidden_fields=JOB_SUBMISSION_HIDDEN_FIELDS,
            ),
        ]
    )


def test_create__with_fast_mode_and_no_job_submission(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    tmp_path,
    attach_persona,
    mocker,
):
    application_response = ApplicationResponse(**dummy_application_data[0])

    job_script_data = dummy_job_script_data[0]

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_script_data,
        ),
    )

    sbatch_params = " ".join(f"--sbatch-params={i}" for i in (1, 2, 3))

    param_file_path = tmp_path / "param_file.json"
    param_file_path.write_text(
        json.dumps(
            dict(
                foo="oof",
                bar="rab",
                baz="zab",
            )
        )
    )

    attach_persona("dummy@dummy.com")

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.tools.fetch_application_data",
        return_value=application_response,
    )
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                create --name=dummy-name
                       --application-id={application_response.id}
                       --param-file={param_file_path}
                       --fast
                       --no-submit
                       {sbatch_params}
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert mocked_fetch_application_data.called_once_with(
        dummy_context,
        id=application_response.id,
        identifier=None,
    )
    assert create_route.called
    content = json.loads(create_route.calls.last.request.content)
    assert content == dict(
        param_dict=dict(
            application_config=dict(
                foo="oof",
                bar="rab",
                baz="zab",
            ),
            jobbergate_config=dict(
                default_template="test-job-script.py.j2",
                job_script_name=None,
                output_directory=".",
                supporting_files=None,
                supporting_files_output_name=None,
                template_files=["test-job-script.py.j2"],
                user_supplied_key="user-supplied-value",
            ),
        ),
        application_id=application_response.id,
        job_script_description=None,
        job_script_name="dummy-name",
        sbatch_params=["1", "2", "3"],
    )

    mocked_render.assert_called_once_with(
        dummy_context,
        JobScriptResponse(**job_script_data),
        title="Created Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    job_script_data = dummy_job_script_data[0]
    job_script_id = job_script_data["id"]

    new_job_script_data = {
        **job_script_data,
        "name": "new-test-name",
        "description": "new-test-description",
    }
    respx_mock.put(f"{dummy_domain}/jobbergate/job-scripts/{job_script_id}").mock(
        return_value=httpx.Response(httpx.codes.OK, json=new_job_script_data),
    )
    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update --id={job_script_id}
                       --name='new-test-name'
                       --description='new-test-description'
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        JobScriptResponse(**new_job_script_data),
        title="Updated Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_delete__makes_request_and_sends_terminal_message(
    respx_mock,
    make_test_app,
    dummy_domain,
    cli_runner,
):
    job_script_id = 13

    delete_route = respx_mock.delete(f"{dummy_domain}/jobbergate/job-scripts/{job_script_id}").mock(
        return_value=httpx.Response(httpx.codes.NO_CONTENT),
    )
    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete --id={job_script_id}"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "JOB SCRIPT DELETE SUCCEEDED"


def test_show_files__success(
    respx_mock,
    make_test_app,
    dummy_job_script_data,
    dummy_job_script_files,
    dummy_domain,
    cli_runner,
    mocker,
):
    """
    Verify that the ``show-files`` subcommand works as expected.
    """
    respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_script_data[0],
        ),
    )
    test_app = make_test_app("show-files", show_files)
    mocked_terminal_message = mocker.patch("jobbergate_cli.subapps.job_scripts.app.terminal_message")

    result = cli_runner.invoke(test_app, shlex.split("show-files --id=1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_terminal_message.assert_called_once_with(
        dummy_job_script_files["files"]["application.sh"],
        subject="application.sh",
        footer="This is the main job script file",
    )


class TestDownloadJobScriptFiles:
    """
    Test the ``download`` subcommand.
    """

    @pytest.fixture()
    def test_app(self, make_test_app):
        """
        Fixture to create a test app.
        """
        return make_test_app("download", download_files)

    def test_download__success(
        self,
        respx_mock,
        test_app,
        dummy_job_script_data,
        dummy_domain,
        cli_runner,
        mocker,
        tmp_path,
        dummy_template_source,
    ):
        """
        Test that the ``download`` subcommand works as expected.
        """
        respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/1").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dummy_job_script_data[0],
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.terminal_message")

        with mock.patch.object(pathlib.Path, "cwd", return_value=tmp_path):
            result = cli_runner.invoke(test_app, shlex.split("download --id=1"))

        assert result.exit_code == 0, f"download failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            "A total of 1 job script files were successfully downloaded.",
            subject="Job script download succeeded",
        )

        desired_list_of_files = {tmp_path / "application.sh"}
        assert set(tmp_path.rglob("*")) == set(desired_list_of_files)
        assert (tmp_path / "application.sh").read_text() == dummy_template_source

    def test_download__fail(
        self,
        respx_mock,
        test_app,
        dummy_domain,
        cli_runner,
    ):
        """
        Test that the ``download`` subcommand fails when the job script does not exist.
        """
        respx_mock.get(f"{dummy_domain}/jobbergate/job-scripts/1").mock(
            return_value=httpx.Response(
                httpx.codes.NOT_FOUND,
            ),
        )

        with mock.patch("jobbergate_cli.subapps.job_scripts.tools.save_job_script_files") as mocked:
            result = cli_runner.invoke(test_app, shlex.split("download --id=1"))
            mocked.assert_not_called()

        assert result.exit_code == 1
