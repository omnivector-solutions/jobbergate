"""
Tests for the /job-scripts/ endpoint.
"""
import json
from datetime import datetime
from io import StringIO
from textwrap import dedent
from unittest import mock

import nest_asyncio
import pytest
from botocore.exceptions import BotoCoreError
from fastapi import status
from fastapi.exceptions import HTTPException

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_scripts.routers import (
    build_job_script_data_as_string,
    get_s3_object_as_tarfile,
    inject_sbatch_params,
    render_template,
)
from jobbergateapi2.apps.job_scripts.schemas import JobScript
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.fixture
def job_script_data_as_string():
    """
    Example of a default application script.
    """
    content = json.dumps(
        {
            "application.sh": dedent(
                """\
                            #!/bin/bash

                            #SBATCH --job-name=rats
                            #SBATCH --partition=debug
                            #SBATCH --output=sample-%j.out


                            echo $SLURM_TASKS_PER_NODE
                            echo $SLURM_SUBMIT_DIR"""
            )
        }
    )
    return content


@pytest.fixture
def new_job_script_data_as_string():
    """
    Example of an application script after the injection of the sbatch params.
    """
    content = json.dumps(
        {
            "application.sh": dedent(
                """\
                            #!/bin/bash

                            #SBATCH --comment=some_comment
                            #SBATCH --nice=-1
                            #SBATCH -N 10
                            #SBATCH --job-name=rats
                            #SBATCH --partition=debug
                            #SBATCH --output=sample-%j.out


                            echo $SLURM_TASKS_PER_NODE
                            echo $SLURM_SUBMIT_DIR"""
            )
        }
    )
    return content


@pytest.fixture
def sbatch_params():
    """
    String content of the argument --sbatch-params.
    """
    return ["--comment=some_comment", "--nice=-1", "-N 10"]


def test_inject_sbatch_params(job_script_data_as_string, sbatch_params, new_job_script_data_as_string):
    """
    Test the injection of sbatch params in a default application script.
    """
    injected_string = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert injected_string == new_job_script_data_as_string


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_job_script(
    boto3_client_mock, job_script_data, param_dict, application_data, client, user_data, s3_object
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
    s3_client_mock.get_object.return_value = s3_object

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
    query = job_scripts_table.select(job_scripts_table.c.id == 1)
    job_script = JobScript.parse_obj(await database.fetch_one(query))

    assert job_script is not None
    assert job_script.job_script_name == job_script_data["job_script_name"]


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


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
@database.transaction(force_rollback=True)
async def test_get_s3_object_as_tarfile(boto3_client_mock, param_dict, s3_object):
    """
    Test getting a file from S3 with get_s3_object function.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    s3_client_mock.get_object.return_value = s3_object

    s3_file = get_s3_object_as_tarfile(1, 1)

    assert s3_file is not None
    s3_client_mock.get_object.assert_called_once()


@mock.patch("jobbergateapi2.apps.job_scripts.routers.boto3")
def test_get_s3_object_not_found(
    boto3_client_mock,
    param_dict,
):
    """
    Test exception when file not exists in S3 for get_s3_object function.
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    s3_client_mock.get_object.side_effect = BotoCoreError()

    s3_file = None
    with pytest.raises(HTTPException) as exc:
        s3_file = get_s3_object_as_tarfile(1, 1)

    assert "Application with id=1 not found for user=1" in str(exc)

    assert s3_file is None
    s3_client_mock.get_object.assert_called_once()


def test_render_template(param_dict_flat, template_files, job_script_data_as_string):
    """
    Test correctly rendered template for job_script template.
    """
    job_script_rendered = render_template(template_files, param_dict_flat)

    assert job_script_rendered == job_script_data_as_string


def test_build_job_script_data_as_string(s3_object_as_tar, param_dict, job_script_data_as_string):
    """
    Test build_job_script_data_as_string function correct output.
    """
    data_as_string = build_job_script_data_as_string(s3_object_as_tar, param_dict)

    assert data_as_string == job_script_data_as_string


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_script_by_id(client, user_data, application_data, job_script_data):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 1

    response = client.get("/job-scripts/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["job_script_name"] == job_script_data["job_script_name"]
    assert data["job_script_data_as_string"] == job_script_data["job_script_data_as_string"]
    assert data["job_script_owner_id"] == 1
    assert data["application_id"] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_script_by_id_invalid(client, user_data):
    """
    Test the correct response code is returned when a job_script does not exist.

    This test proves that GET /job-script/<id> returns the correct response code when the
    requested job_script does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_script requested doesn't exist (404).
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/job-scripts/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_script_from_user(client, user_data, application_data, job_script_data):
    """
    Test GET /job-scripts/ returns only job_scripts owned by the user making the request.

    This test proves that GET /job-scripts/ returns the correct job_scripts for the user making
    the request. We show this by asserting that the job_scripts returned in the response are
    only job_scripts owned by the user making the request.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data.pop("job_script_owner_id")
    job_scripts = [
        JobScript(id=1, job_script_owner_id=1, **job_script_data),
        JobScript(id=2, job_script_owner_id=999, **job_script_data),
        JobScript(id=3, job_script_owner_id=1, **job_script_data),
    ]
    await insert_objects(job_scripts, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 3

    response = client.get("/job-scripts/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 3


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_script_from_user_empty(client, user_data, application_data, job_script_data):
    """
    Test job_script_list doesn't include job_scripts owned by other users.

    This test proves that the user making the request cannot see job_scripts owned by other users.
    We show this by creating job_scripts that are owned by another user id and assert that
    the user making the request to /job-scripts/ doesn't see any of the other user's
    job_scripts in the response, len(response.json()) == 0.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data.pop("job_script_owner_id")
    job_scripts = [
        JobScript(id=1, job_script_owner_id=999, **job_script_data),
        JobScript(id=2, job_script_owner_id=999, **job_script_data),
        JobScript(id=3, job_script_owner_id=999, **job_script_data),
    ]
    await insert_objects(job_scripts, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 3

    response = client.get("/job-scripts/")
    assert response.status_code == status.HTTP_200_OK

    assert len(response.json()) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_script_all(client, user_data, application_data, job_script_data):
    """
    Test that listing job_scripts, when all=True, contains job_scripts owned by other users.

    This test proves that the user making the request can see job_scripts owned by other users.
    We show this by creating three job_scripts, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-scripts/?all=True includes all three
    job_scripts.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script_data.pop("job_script_owner_id")
    job_scripts = [
        JobScript(id=1, job_script_owner_id=1, **job_script_data),
        JobScript(id=2, job_script_owner_id=999, **job_script_data),
        JobScript(id=3, job_script_owner_id=1, **job_script_data),
    ]
    await insert_objects(job_scripts, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 3

    response = client.get("/job-scripts/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2
    assert data[2]["id"] == 3


@pytest.mark.freeze_time
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_job_script(client, user_data, application_data, job_script_data):
    """
    Test update job_script via PUT.

    This test proves that the job_script values are correctly updated following a PUT request to the
    /job-scripts/<id> endpoint. We show this by assert the response status code to 201, the response data
    it corresponds to the updated data, and the data in the database is also updated.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    response = client.put("/job-scripts/1", data={"job_script_name": "new name"})

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    now = datetime.now()

    assert data["job_script_name"] == "new name"
    assert data["id"] == 1
    assert data["updated_at"] == now.isoformat()

    query = job_scripts_table.select(job_scripts_table.c.id == 1)
    job_script = JobScript.parse_obj(await database.fetch_one(query))

    assert job_script is not None
    assert job_script.job_script_name == "new name"
    assert job_script.updated_at == now


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_job_script_not_found(client, user_data, application_data, job_script_data):
    """
    Test that it is not possible to update a job_script not found.

    This test proves that it is not possible to update a job_script if it is not found. We show this by
    asserting that the response status code of the request is 404, and that the data stored in the
    database for the job_script is no updated.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    response = client.put("/job-scripts/123", data={"job_script_name": "new name"})

    assert response.status_code == status.HTTP_404_NOT_FOUND

    query = job_scripts_table.select(job_scripts_table.c.id == 1)
    job_script = JobScript.parse_obj(await database.fetch_one(query))

    assert job_script is not None
    assert job_script.job_script_name == job_script_data["job_script_name"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_job_script(client, user_data, application_data, job_script_data):
    """
    Test delete job_script via DELETE.

    This test proves that a job_script is successfully deleted via a DELETE request to the /job-scripts/<id>
    endpoint. We show this by asserting that the job_script no longer exists in the database after the
    request is made and the correct status code is returned (204).
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 1

    response = client.delete("/job-scripts/1")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_job_script_not_found(client, user_data, application_data, job_script_data):
    """
    Test that it is not possible to delete a job_script that is not found.

    This test proves that it is not possible to delete a job_script if it does not exists. We show this by
    assert that a 404 response status code is returned and the job_script still exists in the database after
    the request.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 1

    response = client.delete("/job-scripts/123")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_scripts")
    assert count[0][0] == 1
