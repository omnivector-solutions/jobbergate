import sys

from fake_sbatch.config import settings
from fake_sbatch.main import app


def test_prints_out_fake_slurm_job_id_when_roll_is_large_enough(mocker, cli_runner):
    mocker.patch("fake_sbatch.main.random", return_value=settings.FAKE_SBATCH_FAIL_PCT + sys.float_info.epsilon)
    result = cli_runner.invoke(app)
    assert result.exit_code == 0, f"submit failed: {result.stdout}"

    slurm_job_id = int(result.stdout.split(",")[0])
    assert f"{slurm_job_id},fake-sbatch-cluster\n" == result.stdout
    assert settings.FAKE_SBATCH_MIN_JOB_ID <= slurm_job_id <= settings.FAKE_SBATCH_MAX_JOB_ID


def test_exits_with_fail_code_when_roll_is_too_small(mocker, cli_runner):
    mocker.patch("fake_sbatch.main.random", return_value=settings.FAKE_SBATCH_FAIL_PCT - sys.float_info.epsilon)
    result = cli_runner.invoke(app)
    assert result.exit_code == 1, f"submit succeeded but should have failed: {result.stdout}"
