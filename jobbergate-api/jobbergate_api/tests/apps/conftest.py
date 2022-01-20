"""
Pytest helpers to use in all apps.
"""
from pytest import fixture


@fixture
def user_data():
    """
    Default user data for testing.
    """
    return {
        "email": "user1@email.com",
        "full_name": "username",
        "password": "supersecret123456",
        "principals": "role:admin",
    }


@fixture
def application_data():
    """
    Default application data for testing.
    """
    return {
        "application_name": "test_name",
        "application_file": "the\nfile",
        "application_config": "the configuration is here",
    }


@fixture
def job_script_data():
    """
    Default job_script data for testing.
    """
    return {
        "job_script_name": "test_name",
        "job_script_data_as_string": "the\nfile",
        "job_script_owner_email": "owner1@org.com",
    }


@fixture
def job_submission_data():
    """
    Default job_submission data for testing.
    """
    return {
        "job_submission_name": "test_name",
    }
