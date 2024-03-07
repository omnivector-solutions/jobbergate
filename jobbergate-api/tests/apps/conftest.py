"""
Pytest helpers to use in all apps.
"""

from pytest import fixture

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus


@fixture
def base_data(tester_email):
    """
    Provide a fixture that supplies test application data.
    """
    return {
        "name": "test_name",
        "description": "test_description",
        "owner_email": tester_email,
        "is_archived": False,
    }


@fixture
def fill_application_data(base_data):
    """
    Combine user supplied application data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {**base_data, **fields}

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
def fill_job_template_data(base_data):
    """
    Combine user supplied template data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {**base_data, **fields}

    return _helper


@fixture
def fill_all_job_template_data(fill_job_script_data):
    """
    Combine many fields of user supplied template data with defaults.
    """

    def _helper(*all_fields):
        return [fill_job_script_data(**f) for f in all_fields]

    return _helper


@fixture
def fill_job_script_data(base_data):
    """
    Combine user supplied job_script data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {**base_data, **fields}

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
def job_submission_data(base_data):
    """
    Provide a fixture that supplies test job_submission data.
    """
    return {
        **base_data,
        "client_id": "dummy-client-id",
        "status": JobSubmissionStatus.CREATED,
        "sbatch_arguments": ["--name foo", "--comment=bar"],
    }


@fixture
def fill_job_submission_data(job_submission_data):
    """
    Combine user supplied job_script data with defaults. If there are overlaps, use the user supplied data.
    """

    def _helper(**fields):
        return {**job_submission_data, **fields}

    return _helper


@fixture
def fill_all_job_submission_data(fill_job_submission_data):
    """
    Combine many fields of user supplied job_submission data with defaults.
    """

    def _helper(*all_fields):
        return [fill_job_submission_data(**f) for f in all_fields]

    return _helper
