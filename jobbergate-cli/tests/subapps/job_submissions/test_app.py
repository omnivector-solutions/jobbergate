import shlex
from unittest import mock

import httpx
import pytest

from jobbergate_cli.schemas import JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.app import HIDDEN_FIELDS, create, delete, get_one, list_all, style_mapper
from jobbergate_cli.text_tools import unwrap


@pytest.mark.parametrize(
    "flag_name,flag_job_script_id,separator",
    [
        ("--name", "--job-script-id", "="),
        ("-n", "-i", " "),
    ],
)
def test_create(
    make_test_app,
    dummy_context,
    dummy_job_submission_data,
    cli_runner,
    mocker,
    flag_name,
    flag_job_script_id,
    separator,
):
    job_submission_data = JobSubmissionResponse(**dummy_job_submission_data[0])
    job_submission_name = job_submission_data.name
    job_submission_description = job_submission_data.description
    job_script_id = job_submission_data.job_script_id

    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")

    submissions_handler = mock.MagicMock()
    submissions_handler.run.return_value = job_submission_data
    mocked_factory = mocker.patch(
        "jobbergate_cli.subapps.job_submissions.app.job_submissions_factory", return_value=submissions_handler
    )

    test_app = make_test_app("create", create)
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                create {flag_name}{separator}{job_submission_name}
                       --description='{job_submission_description}'
                       {flag_job_script_id}{separator}{job_script_id}
                       --download
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"

    mocked_factory.assert_called_once_with(
        dummy_context,
        job_script_id,
        job_submission_name,
        description=job_submission_description,
        execution_directory=None,
        cluster_name=None,
        sbatch_arguments=None,
        download=True,
    )

    mocked_render.assert_called_once_with(
        dummy_context,
        job_submission_data,
        title="Created Job Submission",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_list_all__renders_paginated_results(
    make_test_app,
    dummy_context,
    cli_runner,
    mocker,
    attach_persona,
):
    test_app = make_test_app("list-all", list_all)
    mocked_pagination = mocker.patch("jobbergate_cli.subapps.job_submissions.app.handle_pagination")
    attach_persona("dummy@dummy.com")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_pagination.assert_called_once_with(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-submissions",
        abort_message="Couldn't retrieve job submissions list from API",
        params={"user_only": True, "sort_ascending": False, "sort_field": "id"},
        title="Job Submission List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
        nested_response_model_cls=JobSubmissionResponse,
        value_mappers=None,
    )


@pytest.mark.parametrize(
    "flag_id,separator",
    [
        ("--id", "="),
        ("-i", " "),
    ],
)
def test_get_one__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
    cli_runner,
    mocker,
    flag_id,
    separator,
    attach_persona,
):
    attach_persona("dummy@dummy.com")
    respx_mock.get(f"{dummy_domain}/jobbergate/job-submissions/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_submission_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split(f"get-one {flag_id}{separator}1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        JobSubmissionResponse(**dummy_job_submission_data[0]),
        title="Job Submission",
        hidden_fields=HIDDEN_FIELDS,
        value_mappers=None,
    )


@pytest.mark.parametrize(
    "flag_id,separator",
    [
        ("--id", "="),
        ("-i", " "),
    ],
)
def test_delete__makes_request_and_sends_terminal_message(
    respx_mock,
    make_test_app,
    dummy_domain,
    cli_runner,
    flag_id,
    separator,
):
    job_submission_id = 13

    delete_route = respx_mock.delete(f"{dummy_domain}/jobbergate/job-submissions/{job_submission_id}").mock(
        return_value=httpx.Response(httpx.codes.NO_CONTENT),
    )
    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete {flag_id}{separator}{job_submission_id}"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "JOB SUBMISSION DELETE SUCCEEDED"
