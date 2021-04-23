"""
Tests for the /job-scripts/ endpoint.
"""
import json
from io import StringIO
from unittest import mock

import nest_asyncio
import pytest
from botocore.exceptions import BotoCoreError
from fastapi import status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_job_script(
    boto3_client_mock, job_script_data, param_dict, application_data, client, user_data
):
    """
    Test POST /job_scripts/ correctly creates a job_script.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint. We show this by asserting that the job_script is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))
    s3_client_mock.get_object.return_value = {
        "Body": open("jobbergateapi2/tests/apps/job_scripts/jobbergate.tar.gz", "rb")
    }

    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)
    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data["param_dict"] = json.dumps(param_dict)
    response = client.post("/job-scripts/", data=job_script_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_201_CREATED
    s3_client_mock.get_object.assert_called_once()

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 1


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_job_script_without_application(
    boto3_client_mock, job_script_data, param_dict, client, user_data
):
    """
    Test that is not possible to create a job_script without an application.

    This test proves that is not possible to create a job_script without an existing application.
    We show this by trying to create a job_script without an application created before, then assert that the
    job_script still does not exists in the database, the correct status code (404) is returned and that the
    boto3 method is never called.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    job_script_data["param_dict"] = json.dumps(param_dict)
    response = client.post("/job-scripts/", data=job_script_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    s3_client_mock.get_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_job_script_wrong_user(
    boto3_client_mock, job_script_data, param_dict, application_data, client, user_data
):
    """
    Test that is not possible to create a job_script based in an application of another user.

    This test proves that is not possible to create a job_script with another user's application.
    We show this by trying to create a job_script with an application from another user (id=999), then assert
    that the job_script still does not exists in the database, the correct status code (404) is returned and
    that the boto3 method is never called.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)
    application = [Application(id=1, application_owner_id=999, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data["param_dict"] = json.dumps(param_dict)
    response = client.post("/job-scripts/", data=job_script_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    s3_client_mock.get_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_job_script_file_not_found(
    boto3_client_mock, job_script_data, param_dict, application_data, client, user_data
):
    """
    Test that is not possible to create a job_script if the application is in the database but not in S3.

    This test proves that is not possible to create a job_script with an existing application in the
    database but not in S3, this covers for when for some reason the application file in S3 is deleted but it
    remains in the database. We show this by trying to create a job_script with an existing application that
    is not in S3 (raises BotoCoreError), then assert that the job_script still does not exists in the
    database, the correct status code (404) is returned and that the boto3 method was called.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))
    s3_client_mock.get_object.side_effect = BotoCoreError()

    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)
    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data["param_dict"] = json.dumps(param_dict)
    response = client.post("/job-scripts/", data=job_script_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    s3_client_mock.get_object.assert_called_once()

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 0
