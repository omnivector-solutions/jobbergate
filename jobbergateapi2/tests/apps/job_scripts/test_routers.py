"""
Tests for the /job-scripts/ endpoint.
"""
import json
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
from jobbergateapi2.apps.job_scripts.routers import (
    build_job_script_data_as_string,
    get_s3_object_as_tarfile,
    inject_sbatch_params,
    render_template,
)
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
