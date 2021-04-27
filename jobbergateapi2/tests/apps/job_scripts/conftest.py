from pytest import fixture


@fixture
def job_script_data():
    """
    Default job_script data for testing.
    """
    return {
        "job_script_name": "test_name",
        "job_script_data_as_string": "the\nfile",
        "job_script_owner_id": 1,
        "application_id": 1,
    }


@fixture
def param_dict():
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
