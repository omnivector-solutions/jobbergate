import subprocess
from textwrap import dedent

import pytest

from jobbergate_core.tools.sbatch import SbatchHandler, inject_sbatch_params


@pytest.fixture()
def sbatch_path(tmp_path):
    path = tmp_path / "sbatch"
    path.write_text("#!/bin/bash\n")
    return path


@pytest.fixture()
def scontrol_path(tmp_path):
    path = tmp_path / "scontrol"
    path.write_text("#!/bin/bash\n")
    return path


class TestSbatchHandler:
    def test_run__success(self, mocker, sbatch_path, scontrol_path, tmp_path):
        response = subprocess.CompletedProcess(args=[], stdout="123,cluster-name", returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = SbatchHandler(
            username="test-user", sbatch_path=sbatch_path, scontrol_path=scontrol_path, submission_directory=tmp_path
        )

        job_script_path = tmp_path / "file.sh"

        assert sbatch_handler.run(job_script_path) == 123
        mocked_run.assert_called_once_with(
            [
                sbatch_path.as_posix(),
                job_script_path.as_posix(),
                "--parsable",
            ],
            user="test-user",
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_run__success_with_no_cluster_name(self, mocker, sbatch_path, scontrol_path, tmp_path):
        response = subprocess.CompletedProcess(args=[], stdout="123", returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = SbatchHandler(
            username="test-user", sbatch_path=sbatch_path, scontrol_path=scontrol_path, submission_directory=tmp_path
        )

        job_script_path = tmp_path / "file.sh"

        assert sbatch_handler.run(job_script_path) == 123
        mocked_run.assert_called_once_with(
            [
                sbatch_path.as_posix(),
                job_script_path.as_posix(),
                "--parsable",
            ],
            user="test-user",
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_run__fail_on_sbatch_error(self, mocker, sbatch_path, scontrol_path, tmp_path):
        mocker.patch(
            "jobbergate_core.tools.sbatch.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "sbatch", stderr="Error: Invalid argument"),
        )

        sbatch_handler = SbatchHandler(
            username="test-user", sbatch_path=sbatch_path, scontrol_path=scontrol_path, submission_directory=tmp_path
        )
        job_script_path = tmp_path / "file.sh"

        with pytest.raises(
            RuntimeError,
            match="^Failed to run command with code 1: Error: Invalid argument",
        ):
            sbatch_handler.run(job_script_path)

    @pytest.mark.parametrize("stdout", ["", "not-a-number"])
    def test_run__fail_on_unparsable_output(self, mocker, stdout, sbatch_path, scontrol_path, tmp_path):
        response = subprocess.CompletedProcess(args=[], stdout=stdout, returncode=0)
        mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = SbatchHandler(
            username="test-user", sbatch_path=sbatch_path, scontrol_path=scontrol_path, submission_directory=tmp_path
        )

        job_script_path = tmp_path / "file.sh"

        with pytest.raises(
            RuntimeError,
            match="^Failed to parse slurm job id from",
        ):
            sbatch_handler.run(job_script_path)


class TestInjectSbatchParameters:
    def test_with_header(self):
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

        actual_result = inject_sbatch_params(
            job_script_data_as_string, sbatch_params, "Sbatch params injected at rendering time"
        )
        assert actual_result == expected_result

    def test_inject_sbatch_params__no_sbatch_flag(self):
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

            #SBATCH --comment=some_comment
            #SBATCH --nice=-1
            #SBATCH -N 10

            echo $SLURM_TASKS_PER_NODE
            echo $SLURM_SUBMIT_DIR
            """
        )

        actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
        assert actual_result == expected_result

    def test_inject_sbatch_params__empty_list(self):
        sbatch_params = []

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

            echo $SLURM_TASKS_PER_NODE
            echo $SLURM_SUBMIT_DIR
            """
        )

        actual_result = inject_sbatch_params(
            job_script_data_as_string, sbatch_params, "Sbatch params injected at rendering time"
        )
        assert actual_result == expected_result
