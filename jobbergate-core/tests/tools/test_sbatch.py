import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

import pytest

from jobbergate_core.tools.sbatch import InfoHandler, SubmissionHandler, inject_sbatch_params


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


class TestSubmissionHandler:
    @pytest.mark.parametrize(
        "sbatch_output, expected_result",
        [
            ("123", {"id": "123", "cluster_name": None}),
            ("123,cluster", {"id": "123", "cluster_name": "cluster"}),
        ],
    )
    def test_parse_sbatch_parser(self, sbatch_output, expected_result):
        actual_result = SubmissionHandler.sbatch_output_parser.match(sbatch_output).groupdict()
        assert actual_result == expected_result

    def test_run__success(self, mocker, sbatch_path, tmp_path):
        response = subprocess.CompletedProcess(args=[], stdout="123", returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = SubmissionHandler(
            sbatch_path=sbatch_path,
            submission_directory=tmp_path,
        )

        job_script_path = tmp_path / "file.sh"

        assert sbatch_handler.submit_job(job_script_path) == 123
        mocked_run.assert_called_once_with(
            (
                sbatch_path.as_posix(),
                "--parsable",
                job_script_path.as_posix(),
            ),
            check=True,
            shell=False,
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

    def test_run__fail_on_sbatch_error(self, mocker, sbatch_path, tmp_path):
        mocker.patch(
            "jobbergate_core.tools.sbatch.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "sbatch", stderr="Error: Invalid argument"),
        )

        sbatch_handler = SubmissionHandler(sbatch_path=sbatch_path, submission_directory=tmp_path)
        job_script_path = tmp_path / "file.sh"

        with pytest.raises(
            RuntimeError,
            match="^Failed to run command with code 1: Error: Invalid argument",
        ):
            sbatch_handler.submit_job(job_script_path)

    @pytest.mark.parametrize("stdout", ["", "not-a-number"])
    def test_run__fail_on_unparsable_output(self, mocker, stdout, sbatch_path, tmp_path):
        response = subprocess.CompletedProcess(args=[], stdout=stdout, returncode=0)
        mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = SubmissionHandler(sbatch_path=sbatch_path, submission_directory=tmp_path)

        job_script_path = tmp_path / "file.sh"

        with pytest.raises(
            RuntimeError,
            match="^Failed to parse slurm job id from",
        ):
            sbatch_handler.submit_job(job_script_path)

    def test_file_to_submission__success(self, sbatch_path, tmp_path):
        sbatch_handler = SubmissionHandler(
            sbatch_path=sbatch_path,
            submission_directory=tmp_path,
        )

        with TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir) / "file.txt"
            file_content = b"test"
            source_file.write_bytes(file_content)
            destination_file = sbatch_handler.copy_file_to_submission_directory(source_file)
            assert destination_file == tmp_path / source_file.name
            assert destination_file.read_bytes() == file_content


class TestInfoHandler:
    def test_get_job_info__success(self, mocker, scontrol_path):
        job_info = {"id": 123, "cluster_name": "cluster", "status": "running", "user": "test-user"}
        response_data = json.dumps({"jobs": [job_info]})
        response = subprocess.CompletedProcess(args=[], stdout=response_data, returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = InfoHandler(scontrol_path=scontrol_path)

        assert sbatch_handler.get_job_info(123) == job_info
        mocked_run.assert_called_once_with(
            (
                scontrol_path.as_posix(),
                "show",
                "job",
                "123",
                "--json",
            ),
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        )

    def test_get_job_info__failed_to_parse(self, mocker, scontrol_path):
        response_data = json.dumps({"foo": "bar"})
        response = subprocess.CompletedProcess(args=[], stdout=response_data, returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = InfoHandler(scontrol_path=scontrol_path)

        with pytest.raises(RuntimeError, match="^Failed to parse job info from"):
            sbatch_handler.get_job_info(123)

        mocked_run.assert_called_once_with(
            (
                scontrol_path.as_posix(),
                "show",
                "job",
                "123",
                "--json",
            ),
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        )

    def test_get_job_info__not_fount(self, mocker, sbatch_path, scontrol_path, tmp_path):
        response_data = json.dumps({"jobs": []})
        response = subprocess.CompletedProcess(args=[], stdout=response_data, returncode=0)
        mocked_run = mocker.patch("jobbergate_core.tools.sbatch.subprocess.run", return_value=response)

        sbatch_handler = InfoHandler(scontrol_path=scontrol_path)
        with pytest.raises(RuntimeError, match="^Job not fount: 123"):
            sbatch_handler.get_job_info(123)
        mocked_run.assert_called_once_with(
            (
                scontrol_path.as_posix(),
                "show",
                "job",
                "123",
                "--json",
            ),
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        )


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
