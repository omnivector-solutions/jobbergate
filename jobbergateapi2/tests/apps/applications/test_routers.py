"""
Tests for the /applications endpoint
"""
from io import StringIO
from unittest import mock

import nest_asyncio
import pytest
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
@mock.patch("jobbergateapi2.apps.applications.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create(boto3_client_mock, application_data, client, user_data):
    """
    Test creating a application
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.post("/applications/", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_200_OK
    s3_client_mock.put_object.assert_called_once()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.applications.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_without_application_name(boto3_client_mock, application_data, client, user_data):
    """
    Don't create application when required value is missing
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    application_data["application_name"] = None
    response = client.post("/applications/", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    s3_client_mock.put_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch("jobbergateapi2.apps.applications.routers.boto3")
@database.transaction(force_rollback=True)
async def test_create_without_file(boto3_client_mock, application_data, client, user_data):
    """
    Don't create application without file
    """
    s3_client_mock = mock.Mock()
    boto3_client_mock.client.return_value = s3_client_mock

    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    application_data["application_name"] = None
    response = client.post("/applications/", data=application_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    s3_client_mock.put_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application(client, user_data, application_data):
    """
    Test delete an application
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    response = client.delete("/applications/1")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_not_from_user(client, user_data, application_data):
    """
    Do nothing if current user id is not the owner of the application
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=999, **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    response = client.delete("/applications/1")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_not_found(client, user_data, application_data):
    """
    Do nothing if application id does not exists
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    response = client.delete("/applications/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_without_id(client, user_data, application_data):
    """
    Don't accept DELETE in /applications/ without id
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.delete("/applications/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_by_id(client, user_data, application_data):
    """
    Return the application with the given id
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    response = client.get("/applications/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["application_name"] == application_data["application_name"]
    assert data["application_config"] == application_data["application_config"]
    assert data["application_file"] == application_data["application_file"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_by_id_invalid(client, user_data, application_data):
    """
    Return 404 when the application id does not exists
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/applications/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_all_from_user(client, user_data, application_data):
    """
    Return all applications from the user
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    applications = [
        Application(id=1, application_owner_id=1, **application_data),
        Application(id=2, application_owner_id=1, **application_data),
        Application(id=3, application_owner_id=999, **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    response = client.get("/applications/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_all_from_user_empty(client, user_data, application_data):
    """
    Return all applications from the user, even when the user don't have any
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    applications = [
        Application(id=1, application_owner_id=999, **application_data),
        Application(id=2, application_owner_id=999, **application_data),
        Application(id=3, application_owner_id=999, **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    response = client.get("/applications/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_all_applications(client, user_data, application_data):
    """
    If all=True returns all applications
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    applications = [
        Application(id=1, application_owner_id=1, **application_data),
        Application(id=2, application_owner_id=1, **application_data),
        Application(id=3, application_owner_id=999, **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    response = client.get("/applications/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2
    assert data[2]["id"] == 3
