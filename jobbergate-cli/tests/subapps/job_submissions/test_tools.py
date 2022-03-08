import json
import copy
from unittest import mock

import httpx
import pytest

from jobbergate_cli.subapps.job_submissions.tools import run_job_script, create_job_submission
from jobbergate_cli.schemas import Persona, IdentityData, TokenSet
from jobbergate_cli.exceptions import Abort


def test_run_job_script__success(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    job_script_data = dummy_job_script_data[0]
    job_script_name = job_script_data["job_script_name"]

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with mock.patch("jobbergate_cli.subapps.job_submissions.tools.subprocess.run") as patched_run:
            patched_run.return_value = mock.MagicMock(
                returncode=0,
                stdout="only the last value matters and it is 13",
            )
            slurm_job_id = run_job_script(job_script_data, "dummy-application-name", build_path=build_path)

            assert slurm_job_id == 13
            patched_run.assert_called_once_with(
                [sbatch_path, build_path / f"{job_script_name}.job", "dummy-application-name"],
                capture_output=True,
                text=True,
                input="sbatch output",
            )
            built_script_path = build_path / f"{job_script_name}.job"
            assert built_script_path.exists()
            assert built_script_path.read_text() == json.loads(
                job_script_data["job_script_data_as_string"]
            )["application.sh"]


def test_run_job_script__raises_Abort_if_SBATCH_PATH_does_not_exist(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    job_script_data = dummy_job_script_data[0]

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with pytest.raises(Abort, match="sbatch executable was not found"):
            run_job_script(job_script_data, "dummy-application-name", build_path=build_path)


def test_run_job_script__raises_Abort_if_build_path_does_not_exist(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"

    job_script_data = dummy_job_script_data[0]

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with pytest.raises(Abort, match="build directory does not exist"):
            run_job_script(job_script_data, "dummy-application-name", build_path=build_path)


def test_run_job_script__uses_temporary_directory_if_build_path_is_None(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    job_script_data = dummy_job_script_data[0]
    job_script_name = job_script_data["job_script_name"]

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with mock.patch("jobbergate_cli.subapps.job_submissions.tools.tempfile.TemporaryDirectory") as patched_temp_dir:
            magic_dir = mock.MagicMock()
            magic_dir.configure_mock(name=str(build_path))
            patched_temp_dir.return_value = magic_dir

            with mock.patch("jobbergate_cli.subapps.job_submissions.tools.subprocess.run") as patched_run:
                patched_run.return_value = mock.MagicMock(
                    returncode=0,
                    stdout="only the last value matters and it is 13",
                )
                slurm_job_id = run_job_script(job_script_data, "dummy-application-name")

                assert slurm_job_id == 13
                patched_run.assert_called_once_with(
                    [sbatch_path, build_path / f"{job_script_name}.job", "dummy-application-name"],
                    capture_output=True,
                    text=True,
                    input="sbatch output",
                )
                built_script_path = build_path / f"{job_script_name}.job"
                assert built_script_path.exists()
                assert built_script_path.read_text() == json.loads(
                    job_script_data["job_script_data_as_string"]
                )["application.sh"]


def test_run_job_script__raises_abort_if_no_executable_script_was_found(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    job_script_data = copy.deepcopy(dummy_job_script_data[0])
    job_script_data["job_script_data_as_string"] = json.dumps(
        {
            k: v for (k, v) in
            json.loads(job_script_data["job_script_data_as_string"]).items()
            if k != "application.sh"
        }
    )

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with pytest.raises(Abort, match="Could not find an executable"):
            run_job_script(job_script_data, "dummy-application-name", build_path=build_path)


def test_run_job_script__raises_abort_if_exit_code_from_sbatch_is_not_0(tweak_settings, tmp_path, dummy_job_script_data):
    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    job_script_data = dummy_job_script_data[0]

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with mock.patch("jobbergate_cli.subapps.job_submissions.tools.subprocess.run") as patched_run:
            patched_run.return_value = mock.MagicMock(
                returncode=1,
                stdout="won't matter because return code is not 0",
                stderr="BOOM!",
            )
            with pytest.raises(Abort, match="job submission with error: BOOM!"):
                run_job_script(job_script_data, "dummy-application-name", build_path=build_path)


def test_create_job_submission__success(
    tweak_settings,
    tmp_path,
    dummy_application_data,
    dummy_job_script_data,
    dummy_job_submission_data,
    respx_mock,
    dummy_domain,
    dummy_context,
):
    application_data = dummy_application_data[0]
    application_id = application_data["id"]

    job_script_data = dummy_job_script_data[0]
    job_script_id = job_script_data["id"]

    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["job_submission_name"]
    job_submission_description = job_submission_data["job_submission_description"]

    fetch_application_route = respx_mock.get(f"{dummy_domain}/applications/{application_id}")
    fetch_application_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=application_data,
        ),
    )

    fetch_job_script_route = respx_mock.get(f"{dummy_domain}/job-scripts/{job_script_id}")
    fetch_job_script_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=job_script_data,
        ),
    )

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    sbatch_path = tmp_path / "dummy-sbatch"
    sbatch_path.write_text("whatever")

    build_path = tmp_path / "dummy-build"
    build_path.mkdir()

    dummy_context.persona = Persona(
        token_set=TokenSet(access_token="foo"),
        identity_data=IdentityData(
            user_email="dummy@dummy.com",
            org_name="dumb-org",
        ),
    )

    with tweak_settings(SBATCH_PATH=sbatch_path):
        with mock.patch("jobbergate_cli.subapps.job_submissions.tools.subprocess.run") as patched_run:
            patched_run.return_value = mock.MagicMock(
                returncode=0,
                stdout="only the last value matters and it is 21",
            )
            new_job_submission = create_job_submission(
                dummy_context,
                job_script_id,
                job_submission_name,
                job_submission_description,
            )
            assert new_job_submission == job_submission_data
