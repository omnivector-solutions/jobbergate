"""
Pytest helpers to use in all apps.
"""
from pytest import fixture

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus


@fixture
def application_data():
    """
    Provide a fixture that supplies test application data.
    """
    return {
        "application_owner_email": "test@email.com",
        "application_name": "test_name",
    }


@fixture
def fill_application_data(application_data):
    """
    Combine user supplied application data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {
            **application_data,
            **fields,
        }

    return _helper


@fixture
def fill_all_application_data(fill_application_data):
    """
    Combine many fields of user supplied application data with defaults.
    """

    def _helper(*all_fields):
        return [fill_application_data(**f) for f in all_fields]

    return _helper


@fixture
def job_script_data():
    """
    Provide a fixture that supplies test job_script data.
    """
    return {
        "job_script_name": "test_name",
        "job_script_owner_email": "owner1@org.com",
    }


@fixture
def fill_job_script_data(job_script_data):
    """
    Combine user supplied job_script data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {
            **job_script_data,
            **fields,
        }

    return _helper


@fixture
def fill_all_job_script_data(fill_job_script_data):
    """
    Combine many fields of user supplied job_script data with defaults.
    """

    def _helper(*all_fields):
        return [fill_job_script_data(**f) for f in all_fields]

    return _helper


@fixture
def job_submission_data():
    """
    Provide a fixture that supplies test job_submission data.
    """
    return {
        "job_submission_name": "test_name",
        "job_submission_owner_email": "owner1@org.com",
        "client_id": "dummy-client-id",
        "status": JobSubmissionStatus.CREATED,
    }


@fixture
def fill_job_submission_data(job_submission_data):
    """
    Combine user supplied job_script data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {
            **job_submission_data,
            **fields,
        }

    return _helper


@fixture
def fill_all_job_submission_data(fill_job_submission_data):
    """
    Combine many fields of user supplied job_submission data with defaults.
    """

    def _helper(*all_fields):
        return [fill_job_submission_data(**f) for f in all_fields]

    return _helper
