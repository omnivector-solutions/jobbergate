"""
Test job-script files.
"""
import snick

from jobbergate_api.apps.job_scripts.tools import inject_sbatch_params


def test_inject_sbatch_params():
    """
    Test the injection of sbatch params in a default application script.
    """

    sbatch_params = ["--comment=some_comment", "--nice=-1", "-N 10"]

    job_script_data_as_string = snick.dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    expected_result = snick.dedent(
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

    actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert actual_result == expected_result


def test_inject_sbatch_params__no_sbatch_flag():
    """
    Test the injection of sbatch params in a default application script.
    """

    sbatch_params = ["--comment=some_comment", "--nice=-1", "-N 10"]

    job_script_data_as_string = snick.dedent(
        """
        #!/bin/bash

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    expected_result = snick.dedent(
        """
        #!/bin/bash

        # Sbatch params injected at rendering time
        #SBATCH --comment=some_comment
        #SBATCH --nice=-1
        #SBATCH -N 10

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    )

    actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert actual_result == expected_result
