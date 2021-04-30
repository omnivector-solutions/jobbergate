from pytest import fixture


@fixture
def job_submission_data():
    """
    Default job_submission data for testing.
    """
    return {
        "job_submission_name": "test_name",
        "job_script_id": 1,
    }
