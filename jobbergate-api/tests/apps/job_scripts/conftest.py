"""
Convenience fixtures for the job scripts tests.
"""

from pytest import fixture

TEST_JOB_SCRIPT_NAME = "test_job_script.sh"


@fixture
def param_dict():
    """
    Provide a fixture that returns a param dict.
    """
    return {
        "application_config": {"job_name": "rats", "partitions": ["debug", "partition1"]},
        "jobbergate_config": {
            "default_template": TEST_JOB_SCRIPT_NAME,
            "job_name": "rats",
            "partition": "debug",
            "supporting_files": [TEST_JOB_SCRIPT_NAME],
            "supporting_files_output_name": {TEST_JOB_SCRIPT_NAME: ["support_file_b.py"]},
            "template_files": [f"templates/{TEST_JOB_SCRIPT_NAME}"],
        },
    }


@fixture
def param_dict_flat():
    """
    Provide a fixture tha returns a flattened pram dict.
    """
    return {
        "job_name": "rats",
        "partitions": ["debug", "partition1"],
        "default_template": TEST_JOB_SCRIPT_NAME,
        "partition": "debug",
        "supporting_files": [TEST_JOB_SCRIPT_NAME],
        "supporting_files_output_name": {TEST_JOB_SCRIPT_NAME: ["support_file_b.py"]},
        "template_files": [f"templates/{TEST_JOB_SCRIPT_NAME}"],
    }


@fixture
def template_files(dummy_template):
    """
    Provide a fixture that creates test template files.
    """
    return {"application.sh": dummy_template}
