import json
import pathlib

import httpx
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission, fetch_job_submission_data, sbatch_run


def test_create_job_submission__success(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
    seed_clusters,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")
    seed_clusters("dummy-cluster")

    new_job_submission = create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        cluster_name="dummy-cluster",
    )
    assert new_job_submission == JobSubmissionResponse(**job_submission_data)


def test_create_job_submission__with_explicit_cluster_name(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
    seed_clusters,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")
    seed_clusters("other-cluster")

    new_job_submission = create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        description=job_submission_description,
        cluster_name="other-cluster",
    )
    assert new_job_submission == JobSubmissionResponse(**job_submission_data)

    assert json.loads(create_job_submission_route.calls.last.request.content)["client_id"] == "other-cluster"


def test_create_job_submission__with_default_cluster_name(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
    seed_clusters,
    tweak_settings,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")
    seed_clusters("other-cluster")

    with tweak_settings(DEFAULT_CLUSTER_NAME="default-cluster"):
        new_job_submission = create_job_submission(
            dummy_context,
            job_script_id,
            job_submission_name,
            description=job_submission_description,
        )
        assert new_job_submission == JobSubmissionResponse(**job_submission_data)

    assert json.loads(create_job_submission_route.calls.last.request.content)["client_id"] == "default-cluster"


def test_create_job_submission__throws_exception_with_no_explicit_or_default_cluster_name(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")

    with pytest.raises(Abort, match="unknown cluster"):
        create_job_submission(
            dummy_context,
            job_script_id,
            job_submission_name,
            description=job_submission_description,
        )


def test_create_job_submission__with_explicit_execution_dir(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
    seed_clusters,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")
    seed_clusters("dummy-cluster")

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        cluster_name="dummy-cluster",
        execution_directory=pathlib.Path("/some/fake/path"),
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] == "/some/fake/path"

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        cluster_name="dummy-cluster",
        execution_directory=pathlib.Path("./some/relative/path"),
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] == str(pathlib.Path.cwd() / "./some/relative/path")


def test_create_job_submission__with_default_execution_dir(
    mocker,
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
    seed_clusters,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["name"]
    job_submission_description = job_submission_data["description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")
    seed_clusters("dummy-cluster")

    mocker.patch("jobbergate_cli.subapps.job_submissions.tools.Path.cwd", return_value=pathlib.Path("/some/fake/path"))

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        cluster_name="dummy-cluster",
        execution_directory=None,
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] == "/some/fake/path"


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


class TestSbatchRun:
    def test_valid_arguments_returns_slurm_id(self, mocker, tweak_settings, tmp_path):
        mocked_popen = mocker.MagicMock()
        mocker.patch("jobbergate_cli.subapps.job_submissions.tools.Popen", return_value=mocked_popen)
        mocked_popen.communicate.return_value = (b"Submitted batch job 123", b"")
        mocked_popen.returncode = 0

        with tweak_settings(SBATCH_PATH=tmp_path):
            slurm_id = sbatch_run("filename.sh")

        assert slurm_id == 123

    def test_raises_abort_if_sbatch_command_returns_non_zero_exit_code(
        self,
        mocker,
        tweak_settings,
        tmp_path,
    ):
        mocked_popen = mocker.MagicMock()
        mocker.patch("jobbergate_cli.subapps.job_submissions.tools.Popen", return_value=mocked_popen)
        mocked_popen.communicate.return_value = (b"", b"Error: Invalid argument")
        mocked_popen.returncode = 1

        with tweak_settings(SBATCH_PATH=tmp_path):
            with pytest.raises(
                Abort,
                match="^Failed to execute submission with error",
            ):
                sbatch_run("filename.sh")

    def test_raises_abort_if_slurm_job_id_cannot_be_parsed_from_output(
        self,
        mocker,
        tweak_settings,
        tmp_path,
    ):
        mocked_popen = mocker.MagicMock()
        mocker.patch("jobbergate_cli.subapps.job_submissions.tools.Popen", return_value=mocked_popen)
        mocked_popen.communicate.return_value = (b"Invalid output", b"")
        mocked_popen.returncode = 0

        with tweak_settings(SBATCH_PATH=tmp_path):
            with pytest.raises(
                Abort,
                match="^Failed to parse slurm job id from output=",
            ):
                sbatch_run("filename.sh")

    def test_raises_abort_if_sbatch_path_not_set_or_does_not_exist(self, tweak_settings, tmp_path):
        with tweak_settings(SBATCH_PATH=tmp_path / "nonexistent"):
            with pytest.raises(
                Abort,
                match="^The path to the sbatch executable is not set or does not exist",
            ):
                sbatch_run("filename.sh")
