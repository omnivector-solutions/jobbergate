"""
Test job-script files.
"""
from textwrap import dedent
from unittest.mock import AsyncMock

import pytest

from jobbergate_api.apps.job_scripts.tools import inject_sbatch_params, render_template_file


def test_inject_sbatch_params():
    """
    Test the injection of sbatch params in a default application script.
    """

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
    ).strip()

    expected_result = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --comment=some_comment
        #SBATCH --nice=-1
        #SBATCH -N 10
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out


        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()

    actual_result = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert actual_result == expected_result


@pytest.mark.asyncio
async def test_render_template(dummy_template):
    """Test the rendering of a template."""
    parameters = {"data": {"job_name": "test_job_name", "partition": "test_partition"}}

    expected_result = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=test_job_name
        #SBATCH --partition=test_partition
        #SBATCH --output=sample-%j.out


        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()

    mocked_file_service = AsyncMock()
    mocked_file_service.get.return_value = dummy_template

    actual_result = await render_template_file(mocked_file_service, dummy_template, parameters)
    assert actual_result == expected_result
