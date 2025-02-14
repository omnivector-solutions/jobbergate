import pathlib
from unittest import mock

import httpx
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import JobScriptResponse, JobSubmissionCreateRequestData, JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.tools import (
    OnsiteJobSubmission,
    RemoteJobSubmission,
    fetch_job_submission_data,
    job_submissions_factory,
)


@pytest.mark.parametrize("submission_cls", [OnsiteJobSubmission, RemoteJobSubmission])
@pytest.mark.parametrize("organization_id", [None, "", "some-organization"])
class TestJobSubmissionsClusterName:
    def test_with_explicit_cluster_name(
        self, dummy_context, attach_persona, submission_cls, organization_id, tweak_settings
    ):
        cluster_name = "test-cluster"
        attach_persona("dummy@dummy.com", organization_id=organization_id)
        with tweak_settings(DEFAULT_CLUSTER_NAME="default-cluster"):
            submission_handler = submission_cls(
                jg_ctx=dummy_context,
                job_script_id=1,
                name="test",
                cluster_name=cluster_name,
            )
        expected_cluster_name = cluster_name
        if organization_id:
            expected_cluster_name += f"-{organization_id}"
        assert submission_handler.cluster_name == expected_cluster_name

    def test_default_cluster_name(self, dummy_context, attach_persona, submission_cls, organization_id, tweak_settings):
        cluster_name = "default-cluster"
        attach_persona("dummy@dummy.com", organization_id=organization_id)
        with tweak_settings(DEFAULT_CLUSTER_NAME=cluster_name):
            submission_handler = submission_cls(
                jg_ctx=dummy_context,
                job_script_id=1,
                name="test",
            )
        expected_cluster_name = cluster_name
        if organization_id:
            expected_cluster_name += f"-{organization_id}"
        assert submission_handler.cluster_name == expected_cluster_name

    def test_throws_exception_with_no_explicit_or_default_cluster_name(
        self, dummy_context, attach_persona, submission_cls, organization_id, tweak_settings
    ):
        attach_persona("dummy@dummy.com", organization_id=organization_id)
        with (
            tweak_settings(DEFAULT_CLUSTER_NAME=None),
            pytest.raises(ValueError, match="No cluster name supplied and no default exists"),
        ):
            submission_cls(
                jg_ctx=dummy_context,
                job_script_id=1,
                name="test",
            )

    def test_with_organization_id_on_cluster_name(
        self, dummy_context, attach_persona, submission_cls, organization_id, tweak_settings
    ):
        cluster_name = "test-cluster"
        if organization_id:
            cluster_name += f"-{organization_id}"
        attach_persona("dummy@dummy.com", organization_id=organization_id)
        with tweak_settings(DEFAULT_CLUSTER_NAME="default-cluster"):
            submission_handler = submission_cls(
                jg_ctx=dummy_context,
                job_script_id=1,
                name="test",
                cluster_name=cluster_name,
            )
        assert submission_handler.cluster_name == cluster_name


@pytest.mark.parametrize("submission_cls", [OnsiteJobSubmission, RemoteJobSubmission])
@pytest.mark.parametrize(
    "execution_directory", [pathlib.Path("./some/relative/path"), pathlib.Path("/some/absolute/path"), None]
)
class TestJobSubmissionsExecutionDirectory:
    def test_execution_directory_is_absolute(self, dummy_context, attach_persona, submission_cls, execution_directory):
        attach_persona("dummy@dummy.com")

        submission_handler = submission_cls(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            execution_directory=execution_directory,
            cluster_name="test-cluster",
        )

        assert submission_handler.execution_directory.is_absolute()

        if execution_directory is None:
            # Default value
            execution_directory = pathlib.Path.home()

        expected_execution_directory = execution_directory.resolve()
        assert submission_handler.execution_directory == expected_execution_directory


class TestJobSubmissionsGetRequestData:
    def test_handle_request_data__on_site(self, dummy_context, attach_persona):
        attach_persona("dummy@dummy.com")

        dummy_data = dict(
            job_script_id=1,
            name="test",
            execution_directory=pathlib.Path("/some/fake/path"),
            sbatch_arguments=["--partition=debug", "--time=1:00:00"],
            description="test description",
            cluster_name="test-cluster",
        )

        submission_handler = OnsiteJobSubmission(jg_ctx=dummy_context, download=True, **dummy_data)

        # simulate process_submission by setting slurm_job_id
        dummy_data["slurm_job_id"] = 1234
        submission_handler.slurm_job_id = dummy_data["slurm_job_id"]

        actual_request_data = submission_handler.get_request_data()
        expected_request_data = JobSubmissionCreateRequestData.model_validate(dummy_data)

        assert actual_request_data == expected_request_data

    def test_handle_request_data__remote(self, dummy_context, attach_persona, dummy_domain, respx_mock):
        attach_persona("dummy@dummy.com")

        dummy_data = dict(
            job_script_id=1,
            name="test",
            execution_directory=pathlib.Path("/some/fake/path"),
            sbatch_arguments=["--partition=debug", "--time=1:00:00"],
            description="test description",
            cluster_name="test-cluster",
        )

        submission_handler = RemoteJobSubmission(jg_ctx=dummy_context, download=True, **dummy_data)

        actual_request_data = submission_handler.get_request_data()
        expected_request_data = JobSubmissionCreateRequestData.model_validate(dummy_data)

        assert actual_request_data == expected_request_data


@pytest.mark.parametrize("submission_cls", [OnsiteJobSubmission, RemoteJobSubmission])
class TestJobSubmissionsMakePostRequest:
    def test_post_request__success(
        self, dummy_context, attach_persona, submission_cls, dummy_job_submission_data, respx_mock, dummy_domain
    ):
        attach_persona("dummy@dummy.com")
        job_submission_data = dummy_job_submission_data[0]

        submission_handler = submission_cls(
            jg_ctx=dummy_context,
            job_script_id=job_submission_data["job_script_id"],
            name=job_submission_data["name"],
            cluster_name="test-cluster",
        )

        create_job_submission_data = JobSubmissionCreateRequestData.model_validate(job_submission_data)
        create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
        create_job_submission_route.mock(
            return_value=httpx.Response(
                httpx.codes.CREATED,
                json=job_submission_data,
            ),
        )

        actual_response = submission_handler.make_post_request(create_job_submission_data)
        expected_response = JobSubmissionResponse.model_validate(job_submission_data)

        assert actual_response == expected_response


class TestJobSubmissionsProcessSubmissions:
    def test_process_submission__remote_download(self, dummy_context, mocker, attach_persona):
        attach_persona("dummy@dummy.com")
        submission_handler = RemoteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            download=True,
        )
        mocked_download_job_script_files = mocker.patch(
            "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files"
        )
        submission_handler.process_submission()
        mocked_download_job_script_files.assert_called_once_with(
            submission_handler.job_script_id, submission_handler.jg_ctx, submission_handler.execution_directory
        )

    def test_process_submission__no_remote_download(self, dummy_context, mocker, attach_persona):
        attach_persona("dummy@dummy.com")
        submission_handler = RemoteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            download=False,
        )
        mocked_download_job_script_files = mocker.patch(
            "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files"
        )
        submission_handler.process_submission()
        mocked_download_job_script_files.assert_not_called()

    def test_process_submission__on_site_abort_if_sbatch_path_is_unset(
        self, dummy_context, attach_persona, tweak_settings
    ):
        attach_persona("dummy@dummy.com")
        submission_handler = OnsiteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
        )

        with (
            tweak_settings(SBATCH_PATH=None),
            pytest.raises(Abort, match="SBATCH_PATH most be set for onsite submissions"),
        ):
            submission_handler.process_submission()

    class DummyFile:
        @property
        def file_type(self):
            return "NOT-ENTRYPOINT"

    @pytest.mark.parametrize("job_script_files", [[], [DummyFile(), DummyFile()]])
    def test_process_submission__on_site_abort_if_not_exact_one_entrypoint_file_is_found(
        self, job_script_files, dummy_context, attach_persona, tweak_settings, mocker, tmp_path
    ):
        attach_persona("dummy@dummy.com")
        submission_handler = OnsiteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
        )

        mocker.patch(
            "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files", return_value=job_script_files
        )

        with (
            tweak_settings(SBATCH_PATH=tmp_path),
            pytest.raises(Abort, match="There should be exactly one entrypoint file in the parent job script"),
        ):
            submission_handler.process_submission()

    @pytest.mark.parametrize("download", [True, False])
    def test_process_submission__on_site_success(
        self, download, dummy_context, attach_persona, tweak_settings, mocker, tmp_path, dummy_job_script_data
    ):
        attach_persona("dummy@dummy.com")

        job_script_data = JobScriptResponse.model_validate(dummy_job_script_data[0])

        submission_handler = OnsiteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            download=download,
            execution_directory=tmp_path,
        )

        mocked_download_job_script_files = mocker.patch(
            "jobbergate_cli.subapps.job_submissions.tools.download_job_script_files", return_value=job_script_data.files
        )
        mocked_inject_sbatch_params = mocker.patch.object(submission_handler, "inject_sbatch_params")

        mocked_sbatch = mock.MagicMock()
        mocked_sbatch.submit_job = lambda *args, **kwargs: 13
        mocker.patch("jobbergate_cli.subapps.job_submissions.tools.SubmissionHandler", return_value=mocked_sbatch)

        with tweak_settings(SBATCH_PATH=tmp_path):
            submission_handler.process_submission()

        assert submission_handler.slurm_job_id == 13

        # files are downloaded anyway for on-site submissions
        mocked_download_job_script_files.assert_called_once_with(1, dummy_context, tmp_path)
        assert mocked_inject_sbatch_params.call_count == 1

    def test_inject_sbatch_params__on_site(self, mocker, attach_persona, dummy_context, tmp_path):
        attach_persona("dummy@dummy.com")
        submission_handler = OnsiteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            execution_directory=tmp_path,
            sbatch_arguments=["--partition=debug", "--time=1:00:00"],
        )

        job_script_path = tmp_path / "entrypoint.sh"

        job_script_path.write_text("original content")

        mocked_inject_sbatch_params = mocker.patch(
            "jobbergate_cli.subapps.job_submissions.tools.inject_sbatch_params", return_value="inject_sbatch_params"
        )

        submission_handler.inject_sbatch_params(job_script_path)

        mocked_inject_sbatch_params.assert_called_once_with(
            "original content", ["--partition=debug", "--time=1:00:00"], "Injected at submission time by Jobbergate CLI"
        )
        assert job_script_path.read_text() == "inject_sbatch_params"

    def test_skip_inject_sbatch_params__on_site(self, mocker, attach_persona, dummy_context, tmp_path):
        attach_persona("dummy@dummy.com")
        submission_handler = OnsiteJobSubmission(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            execution_directory=tmp_path,
            sbatch_arguments=[],
        )

        job_script_path = tmp_path / "entrypoint.sh"

        job_script_path.write_text("original content")

        mocked_inject_sbatch_params = mocker.patch("jobbergate_cli.subapps.job_submissions.tools.inject_sbatch_params")

        submission_handler.inject_sbatch_params(job_script_path)

        assert mocked_inject_sbatch_params.call_count == 0
        assert job_script_path.read_text() == "original content"


@pytest.mark.parametrize("submission_cls", [OnsiteJobSubmission, RemoteJobSubmission])
class TestJobSubmissionsRun:
    def test_run__success(self, dummy_context, attach_persona, submission_cls, mocker):
        attach_persona("dummy@dummy.com")
        submission_handler = submission_cls(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
        )

        mocked_process_submission = mocker.patch.object(submission_handler, "process_submission")
        mocked_get_request_data = mocker.patch.object(
            submission_handler, "get_request_data", return_value="request_data"
        )
        mocked_make_post_request = mocker.patch.object(submission_handler, "make_post_request", return_value="response")

        actual_response = submission_handler.run()

        assert actual_response == "response"
        mocked_process_submission.assert_called_once()
        mocked_get_request_data.assert_called_once()
        mocked_make_post_request.assert_called_once_with("request_data")


@pytest.mark.parametrize(
    "submission_cls,sbatch_path", [[OnsiteJobSubmission, "/usr/bin/sbatch"], [RemoteJobSubmission, None]]
)
def test_job_submissions_factory(submission_cls, sbatch_path, attach_persona, dummy_context, tweak_settings):
    attach_persona("dummy@dummy.com")
    with tweak_settings(SBATCH_PATH=sbatch_path):
        submission_handler = job_submissions_factory(
            jg_ctx=dummy_context,
            job_script_id=1,
            name="test",
            cluster_name="test-cluster",
            download=True,
        )
    assert isinstance(submission_handler, submission_cls)
    assert submission_handler.jg_ctx == dummy_context
    assert submission_handler.job_script_id == 1
    assert submission_handler.name == "test"
    assert submission_handler.cluster_name == "test-cluster"
    assert submission_handler.download is True


def test_fetch_job_submission_data__success__using_id(
    respx_mock,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
):
    job_submission_data = dummy_job_submission_data[3]
    job_submission_id = job_submission_data["id"]
    fetch_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-submissions/{job_submission_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=job_submission_data,
        ),
    )

    result = fetch_job_submission_data(dummy_context, job_submission_id)
    assert fetch_route.called
    assert result == JobSubmissionResponse(**job_submission_data)
    assert result.report_message == job_submission_data.get("report_message")
