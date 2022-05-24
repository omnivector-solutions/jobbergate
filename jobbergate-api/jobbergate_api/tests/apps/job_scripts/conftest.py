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
def template_files_application_content():
    """
    Provide a fixture that creates test application files.
    """
    with open("jobbergate_api/tests/apps/job_scripts/test_files/application.sh") as application_file:
        application_file_content = application_file.read()
    return application_file_content


@fixture
def template_files(template_files_application_content):
    """
    Provide a fixture that creates test template files.
    """
    return {"application.sh": template_files_application_content}
