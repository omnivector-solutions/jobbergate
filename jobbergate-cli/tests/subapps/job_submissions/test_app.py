import shlex
from unittest import mock

import httpx
import pytest

from jobbergate_cli.context import set_active_context
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import JobScriptResponse, JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.app import (
    HIDDEN_FIELDS,
    cancel,
    clone,
    create,
    delete,
    get_one,
    list_all,
    style_mapper,
)
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


def test_create__returns_job_submission_response__remote_mode(
    respx_mock,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
    cli_runner,
    mocker,
    attach_persona,
    tweak_settings,
):
    """Direct invocation of ``create`` in remote mode returns the created ``JobSubmissionResponse``."""
    attach_persona("dummy@dummy.com")
    job_submission_data = dummy_job_submission_data[0]

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions").mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")

    set_active_context(dummy_context)
    with tweak_settings(SBATCH_PATH=None):
        result = create(
            name=job_submission_data["name"],
            job_script_id=job_submission_data["job_script_id"],
            cluster_name="test-cluster",
        )

    expected_response = JobSubmissionResponse(**job_submission_data)
    assert create_route.called
    assert result == expected_response
    mocked_render.assert_called_once_with(
        dummy_context,
        expected_response,
        title="Created Job Submission",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_create__returns_job_submission_response__onsite_mode(
    respx_mock,
    dummy_context,
    dummy_job_submission_data,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
    attach_persona,
    tweak_settings,
    tmp_path,
):
    """Direct invocation of ``create`` in on-site mode returns the created ``JobSubmissionResponse``."""
    attach_persona("dummy@dummy.com")
    job_submission_data = dummy_job_submission_data[0]
    job_script_data = JobScriptResponse.model_validate(dummy_job_script_data[0])

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions").mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")
    mocker.patch(
        "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files",
        return_value=job_script_data.files,
    )
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job.return_value = 13
    mocker.patch("jobbergate_cli.subapps.job_submissions.tools.SubmissionHandler", return_value=mocked_sbatch)

    set_active_context(dummy_context)
    with tweak_settings(SBATCH_PATH=tmp_path):
        result = create(
            name=job_submission_data["name"],
            job_script_id=job_submission_data["job_script_id"],
            cluster_name="test-cluster",
            execution_directory=tmp_path,
        )

    expected_response = JobSubmissionResponse(**job_submission_data)
    assert create_route.called
    assert result == expected_response
    mocked_render.assert_called_once_with(
        dummy_context,
        expected_response,
        title="Created Job Submission",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_create__onsite_sbatch_failure_raises_abort_with_original_error(
    dummy_context,
    dummy_job_script_data,
    mocker,
    attach_persona,
    tweak_settings,
    tmp_path,
):
    """A simulated sbatch failure surfaces as ``Abort`` carrying the underlying error."""
    attach_persona("dummy@dummy.com")
    job_script_data = JobScriptResponse.model_validate(dummy_job_script_data[0])

    mocker.patch(
        "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files",
        return_value=job_script_data.files,
    )
    sbatch_error = RuntimeError("sbatch: error: Batch job submission failed: Invalid partition name specified")
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job.side_effect = sbatch_error
    mocker.patch("jobbergate_cli.subapps.job_submissions.tools.SubmissionHandler", return_value=mocked_sbatch)

    set_active_context(dummy_context)
    with tweak_settings(SBATCH_PATH=tmp_path), pytest.raises(Abort) as exc_info:
        create(
            name="test-submission",
            job_script_id=1,
            cluster_name="test-cluster",
            execution_directory=tmp_path,
        )

    assert exc_info.value.subject == "Slurm Submission Error"
    assert exc_info.value.original_error is sbatch_error
    assert exc_info.value.__cause__ is sbatch_error


def test_create__unexpected_error_raises_abort_with_original_error(dummy_context, mocker):
    """Unexpected errors from the submissions handler surface as ``Abort`` carrying the underlying error."""
    original_error = RuntimeError("BOOM!")
    submissions_handler = mock.MagicMock()
    submissions_handler.run.side_effect = original_error
    mocker.patch("jobbergate_cli.subapps.job_submissions.app.job_submissions_factory", return_value=submissions_handler)

    set_active_context(dummy_context)
    with pytest.raises(Abort) as exc_info:
        create(
            name="test-submission",
            job_script_id=1,
        )

    assert exc_info.value.subject == "Job submission failed"
    assert exc_info.value.original_error is original_error
    assert exc_info.value.__cause__ is original_error


def test_create__preserves_abort_message_from_submission_handler(make_test_app, cli_runner, mocker):
    test_app = make_test_app("create", create)
    submissions_handler = mock.MagicMock()
    submissions_handler.run.side_effect = Abort(
        "Slurm rejected the job submission.\nReason: Invalid partition name specified",
        subject="Slurm Submission Error",
        support=True,
    )

    mocker.patch("jobbergate_cli.subapps.job_submissions.app.job_submissions_factory", return_value=submissions_handler)

    result = cli_runner.invoke(test_app, ["create", "--name", "test-submission", "--job-script-id", "1"])

    assert result.exit_code == 1
    assert "Slurm rejected the job submission." in result.stdout
    assert "Failed to create the job submission" not in result.stdout


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
        params={"user_only": True, "sort_ascending": False, "sort_field": "id", "include_archived": False},
        title="Job Submission List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
        nested_response_model_cls=JobSubmissionResponse,
        value_mappers=None,
        page=None,
        size=50,
    )


def test_list_all__forwards_page_and_size(
    make_test_app,
    dummy_context,
    cli_runner,
    mocker,
    attach_persona,
):
    test_app = make_test_app("list-all", list_all)
    mocked_pagination = mocker.patch("jobbergate_cli.subapps.job_submissions.app.handle_pagination")
    attach_persona("dummy@dummy.com")
    result = cli_runner.invoke(test_app, ["list-all", "--page", "3", "--size", "15"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_pagination.assert_called_once()
    assert mocked_pagination.call_args.kwargs["page"] == 3
    assert mocked_pagination.call_args.kwargs["size"] == 15


def test_list_all__rejects_invalid_page(make_test_app, cli_runner, attach_persona):
    test_app = make_test_app("list-all", list_all)
    attach_persona("dummy@dummy.com")
    result = cli_runner.invoke(test_app, ["list-all", "--page", "-1"])
    assert result.exit_code != 0


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


def test_get_one__returns_job_submission_response(
    respx_mock,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
    mocker,
    attach_persona,
):
    """Direct invocation of ``get_one`` returns the fetched ``JobSubmissionResponse``."""
    attach_persona("dummy@dummy.com")
    respx_mock.get(f"{dummy_domain}/jobbergate/job-submissions/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_submission_data[0],
        ),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")

    set_active_context(dummy_context)
    result = get_one(job_submission_id=1)

    expected_response = JobSubmissionResponse(**dummy_job_submission_data[0])
    assert result == expected_response
    mocked_render.assert_called_once_with(
        dummy_context,
        expected_response,
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


class TestCloneJobSubmission:
    @pytest.mark.parametrize("selector_template", ["{id}", "-i {id}", "--id={id}", "--id {id}"])
    def test_clone__success(
        self,
        respx_mock,
        make_test_app,
        dummy_job_submission_data,
        dummy_domain,
        dummy_context,
        cli_runner,
        mocker,
        selector_template,
    ):
        """
        Test that the clone application subcommand works as expected.
        """

        job_submission_data = dummy_job_submission_data[0]
        job_submission_id = job_submission_data["id"]

        cli_selector = selector_template.format(id=job_submission_id)

        clone_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions/clone/{job_submission_id}").mock(
            return_value=httpx.Response(
                httpx.codes.CREATED,
                json=job_submission_data,
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")

        test_app = make_test_app("clone", clone)
        result = cli_runner.invoke(test_app, shlex.split(f"clone {cli_selector}"))

        assert clone_route.called

        assert result.exit_code == 0, f"clone failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            dummy_context,
            JobSubmissionResponse(**job_submission_data),
            title="Cloned Job Submission",
            hidden_fields=HIDDEN_FIELDS,
        )


class TestCancelJobSubmission:
    @pytest.mark.parametrize("selector_template", ["{id}", "-i {id}", "--id={id}", "--id {id}"])
    def test_cancel__success(
        self,
        respx_mock,
        make_test_app,
        dummy_job_submission_data,
        dummy_domain,
        dummy_context,
        cli_runner,
        mocker,
        selector_template,
    ):
        """
        Test that the cancel application subcommand works as expected.
        """

        job_submission_data = dummy_job_submission_data[0]
        job_submission_id = job_submission_data["id"]

        cli_selector = selector_template.format(id=job_submission_id)

        cancel_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-submissions/cancel/{job_submission_id}").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=job_submission_data,
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.job_submissions.app.render_single_result")

        test_app = make_test_app("cancel", cancel)
        result = cli_runner.invoke(test_app, shlex.split(f"cancel {cli_selector}"))

        assert cancel_route.called

        assert result.exit_code == 0, f"cancel failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            dummy_context,
            JobSubmissionResponse(**job_submission_data),
            title="Cancelled Job Submission",
            hidden_fields=HIDDEN_FIELDS,
        )
