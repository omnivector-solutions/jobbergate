"""
Tests for the /job-scripts/ endpoint.
"""
import json
from io import StringIO
from unittest import mock

import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_scripts.schemas import JobScript
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
    Test POST /job_scripts/ correctly creates an job_script.

    This test proves that an application is successfully created via a POST request to the /applciations/
    endpoint. We show this by asserting that the application is created in the database after the post
    request is made, the correct status code (201) is returned and the correct boto3 method was called.
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
