"""
Define fixtures for the ``jobbergate`` section.
"""
from textwrap import dedent

import pytest


@pytest.fixture(scope="module")
def dummy_template_source():
    """
    Provide a fixture that returns a valid job_script_template.
    """
    return dedent(
        """
        #!/bin/python3

        #SBATCH -t 60
        print("I am a very, very dumb job script")
        print(f"foo='{{foo}}'")
        print(f"bar='{{bar}}'")
        print(f"baz='{{baz}}'")
        """
    ).strip()


@pytest.fixture
def dummy_job_script_files():
    return [
        {
            "parent_id": 1,
            "filename": "application.sh",
            "file_type": "ENTRYPOINT",
        },
    ]


@pytest.fixture
def dummy_pending_job_submission_data(dummy_job_script_files, tmp_path):
    """
    Provide a fixture that returns a dict that is compatible with PendingJobSubmission.
    """
    return dict(
        id=1,
        name="sub1",
        owner_email="email1@dummy.com",
        job_script={"files": dummy_job_script_files},
        slurm_job_id=13,
    )
