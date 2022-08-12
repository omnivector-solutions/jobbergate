"""
Convenience fixtures for the job scripts tests.
"""

from pytest import fixture


@fixture
def param_dict():
    """
    Provide a fixture that returns a param dict.
    """
    return {
        "application_config": {"job_name": "rats", "partitions": ["debug", "partition1"]},
        "jobbergate_config": {
            "default_template": "test_job_script.sh",
            "job_name": "rats",
            "output_directory": ".",
            "partition": "debug",
            "supporting_files": ["test_job_script.sh"],
            "supporting_files_output_name": {"test_job_script.sh": ["support_file_b.py"]},
            "template_files": ["templates/test_job_script.sh"],
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
        "default_template": "test_job_script.sh",
        "output_directory": ".",
        "partition": "debug",
        "supporting_files": ["test_job_script.sh"],
        "supporting_files_output_name": {"test_job_script.sh": ["support_file_b.py"]},
        "template_files": ["templates/test_job_script.sh"],
    }


@fixture
def template_files(dummy_template):
    """
    Provide a fixture that creates test template files.
    """
    return {"application.sh": dummy_template}
