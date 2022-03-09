import shlex

import httpx
import snick

from jobbergate_cli.schemas import ListResponseEnvelope, Pagination
from jobbergate_cli.subapps.job_submissions.app import HIDDEN_FIELDS, create, delete, get_one, list_all, style_mapper


def test_create__full_run_including_non_fast_mode_and_job_submission(
    make_test_app,
    dummy_context,
    dummy_job_submission_data,
    cli_runner,
    mocker,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["job_submission_name"]
    job_submission_description = job_submission_data["job_submission_description"]
    job_script_id = job_submission_data["job_script_id"]

    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")
    patched_create_job_submission = mocker.patch("jobbergate_cli.subapps.job_submissions.app.create_job_submission")
    patched_create_job_submission.return_value = job_submission_data

    test_app = make_test_app("create", create)
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                create --name={job_submission_name}
                       --description='{job_submission_description}'
                       --job-script-id={job_script_id}
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"

    mocked_render.assert_called_once_with(
        dummy_context,
        job_submission_data,
        title="Created Job Submission",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_list_all__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/job-submissions?all=false").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_submission_data,
                pagination=dict(
                    total=3,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_list_results")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_job_submission_data,
            pagination=Pagination(total=3, start=None, limit=None),
        ),
        title="Job Submission List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/job-submissions/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_submission_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split("get-one --id=1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        dummy_job_submission_data[0],
        title="Job Submission",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_delete__makes_request_and_sends_terminal_message(
    respx_mock,
    make_test_app,
    dummy_domain,
    cli_runner,
):
    job_submission_id = 13

    delete_route = respx_mock.delete(f"{dummy_domain}/job-submissions/{job_submission_id}").mock(
        return_value=httpx.Response(httpx.codes.NO_CONTENT),
    )
    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete --id={job_submission_id}"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "JOB SUBMISSION DELETE SUCCEEDED"
