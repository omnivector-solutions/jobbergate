"""
Tests for the /application-permissions/ endpoint.
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.application_permissions.models import application_permissions_table
from jobbergateapi2.apps.application_permissions.schemas import ApplicationPermission
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions(user_data, client):
    """
    Test POST /application-permissions/ correctly create an ApplicationPermission.

    This test proves that an superuser can successfully create an ApplicationPermission by making a request
    to the /application-permissions/. We show this by asserting that the response status code is 201,
    the data in the response is the same as in the request and that the ApplicationPermission exists in the
    database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    acl = {"acl": "Allow|role:admin|view"}
    response = client.post("/application-permissions/", data=acl)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["acl"] == acl["acl"]

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 1

    query = application_permissions_table.select(application_permissions_table.c.id == 1)
    permission = ApplicationPermission.parse_obj(await database.fetch_one(query))

    assert permission is not None
    assert permission.acl == acl["acl"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions_duplicated(user_data, client):
    """
    This test proves that is not possible to create duplicated ApplicationPermission.

    We show this by trying to create the same ApplicationPermission twice, the first one is correctly created
    in the database and the response status code is 201. But the second one receives a 409 status in the
    response and only 1 ApplicationPermission is in the databae and the its id is 1.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    acl = {"acl": "Allow|role:admin|view"}
    response = client.post("/application-permissions/", data={"acl": "Allow|role:admin|view"})
    assert response.status_code == status.HTTP_201_CREATED
    response = client.post("/application-permissions/", data={"acl": "Allow|role:admin|view"})
    assert response.status_code == status.HTTP_409_CONFLICT

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 1

    query = application_permissions_table.select(application_permissions_table.c.id == 1)
    permission = ApplicationPermission.parse_obj(await database.fetch_one(query))

    assert permission is not None
    assert permission.acl == acl["acl"]
    assert permission.id == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions_not_superuser(user_data, client):
    """
    Test that is not possible for a non superuser to create permissions.

    This test proves that is not possible to create an ApplicationPermission. We show this by making a
    request with a non superuser and asserting that the response status code is 401, and that the
    ApplicationPermission is not created in the database.
    """
    user = [UserCreate(is_superuser=False, **user_data)]
    await insert_objects(user, users_table)

    response = client.post("/application-permissions/", data={"acl": "Allow|role:admin|view"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions_invalid_acl(user_data, client):
    """
    Test that is not possible to create an ApplicationPermission with a bad formatted acl.

    This test proves that is not possible to create the ApplicationPermission with a bad formatted acl. We
    show this by making a request with a bad acl string and asserting that the response status code is 400
    and that the ApplicationPermission is not created in the database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    response = client.post("/application-permissions/", data={"acl": "Allow|"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_application_permissions(user_data, client):
    """
    Test the GET in the /application-permissions/ returns the list of existing ApplicationPermissions.

    We show this by creating 2 permissions, making the GET request to the /application-permissions/ endpoint,
    then asserting the response status code is 200, and the content of the response is as expected.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    application_permissions = [
        ApplicationPermission(id=1, acl="Allow|role:admin|create"),
        ApplicationPermission(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(application_permissions, application_permissions_table)

    response = client.get("/application-permissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    assert data[0]["id"] == 1
    assert data[0]["acl"] == "Allow|role:admin|create"
    assert data[1]["id"] == 2
    assert data[1]["acl"] == "Allow|role:admin|view"


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_application_permissions_empty(user_data, client):
    """
    Test the GET in the /application-permissions/ returns the list of existing ApplicationPermissions even
    when there is none.

    We show this by making a request to the /application-permissions/ endpoint, asserting that the response
    status code is 200 and that the contents of the response is empty.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.get("/application-permissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_permissions(user_data, client):
    """
    Test DELETE /application-permissions/{id} by a superuser correctly deletes the ApplicationPermission.

    This test proves that an ApplicationPermission is successfully deleted via a DELETE request to the
    /application-permissions/. We show this this asserting that the ApplicationPermission no longer exists
    in the database and the correct status code (204) is returned.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    application_permissions = [
        ApplicationPermission(id=1, acl="Allow|role:admin|create"),
        ApplicationPermission(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(application_permissions, application_permissions_table)

    response = client.delete("/application-permissions/1")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 1

    query = application_permissions_table.select(application_permissions_table.c.id == 2)
    permission = ApplicationPermission.parse_obj(await database.fetch_one(query))

    assert permission is not None


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_permissions_not_superuser(user_data, client):
    """
    Test that is not possible for a non superuser to delete permissions.

    This test proves that is not possible for a non superuser to delete ApplicationPermission.
    We show this by asserting that the return status code is 401 and the ApplicationPermissions still exists
    in the database.
    """
    user = [UserCreate(is_superuser=False, **user_data)]
    await insert_objects(user, users_table)

    application_permissions = [
        ApplicationPermission(id=1, acl="Allow|role:admin|create"),
        ApplicationPermission(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(application_permissions, application_permissions_table)

    response = client.delete("/application-permissions/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 2


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_permissions_not_found(user_data, client):
    """
    Test that is not possible to delete an ApplicationPermission that doesn't exists.

    This test proves that is not possible to delete an ApplicationPermission that doesn't exists. We show
    this by asserting that the response status code is 404 and that the ApplicationPermissions still exists
    in the database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    application_permissions = [
        ApplicationPermission(id=1, acl="Allow|role:admin|create"),
        ApplicationPermission(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(application_permissions, application_permissions_table)

    response = client.delete("/application-permissions/123")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 2
