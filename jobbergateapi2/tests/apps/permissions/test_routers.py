"""
Tests for the /permissions/ endpoint.
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.permissions.models import application_permissions_table
from jobbergateapi2.apps.permissions.routers import _QUERY_RX
from jobbergateapi2.apps.permissions.schemas import ApplicationPermission
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


def test_query_regex():
    """
    Check if the _QUERY_RX is correct.
    """
    assert _QUERY_RX == r"^(application|job_script|job_submission)$"


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions(user_data, client, permission_class, permission_table, permission_query):
    """
    Test POST /permissions/ correctly create an Permission for each resource.

    This test proves that an superuser can successfully create an Permission by making a request at
    /permissions/. We show this by asserting that the response status code is 201, the data in the response
    is the same as in the request and that the Permission exists in the database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|role:admin|view"}
    response = client.post(f"/permissions/?permission_query={permission_query}", data=data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["acl"] == data["acl"]

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 1

    query = permission_table.select(permission_table.c.id == 1)
    permission = permission_class.parse_obj(await database.fetch_one(query))

    assert permission is not None
    assert permission.acl == data["acl"]


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions_duplicated(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    This test proves that is not possible to create duplicated Permission.

    We show this by trying to create the same Permission twice, the first one is correctly created
    in the database and the response status code is 201. But the second one receives a 409 status in the
    response and only 1 Permission is in the databae and the its id is 1.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|role:admin|view"}
    response = client.post(f"/permissions/?permission_query={permission_query}", data=data)
    assert response.status_code == status.HTTP_201_CREATED
    response = client.post(f"/permissions/?permission_query={permission_query}", data=data)
    assert response.status_code == status.HTTP_409_CONFLICT

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 1

    query = permission_table.select(permission_table.c.id == 1)
    permission = permission_class.parse_obj(await database.fetch_one(query))

    assert permission is not None
    assert permission.acl == data["acl"]
    assert permission.id == 1


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions_not_superuser(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    Test that is not possible for a non superuser to create permissions.

    This test proves that is not possible to create an ApplicationPermission. We show this by making a
    request with a non superuser and asserting that the response status code is 401, and that the
    ApplicationPermission is not created in the database.
    """
    user = [UserCreate(is_superuser=False, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|role:admin|view"}
    response = client.post(f"/permissions/?permission_query={permission_query}", data=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions_without_query_string(user_data, client):
    """
    Test that is not possible to create a Permission without the query string.

    This test proves that is not possible to create the Permission without the query string. We show this
    by making a request without query string and asserting that the response status code is 422.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|role:admin|view"}
    response = client.post("/permissions/", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions_with_bad_query_string(user_data, client):
    """
    Test that is not possible to create a Permission with the query string in wrong format.

    This test proves that is not possible to create the Permission with the query string in wrong format.
    We show this by making a request with the bad query string and asserting that the response status code
    is 422 and that the.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|role:admin|view"}
    response = client.post("/permissions/?permission_query=app", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_permissions_invalid_acl(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    Test that is not possible to create a Permission with a bad formatted acl.

    This test proves that is not possible to create the Permission with a bad formatted acl. We
    show this by making a request with a bad acl string and asserting that the response status code is 400
    and that the Permission is not created in the database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    data = {"acl": "Allow|rw"}
    response = client.post(f"/permissions/?permission_query={permission_query}", data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 0


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_permissions(user_data, client, permission_class, permission_table, permission_query):
    """
    Test the GET in the /permissions/ returns the list of existing Permissions for the given resource.

    We show this by creating 2 permissions, making the GET request to the /permissions/ endpoint,
    then asserting the response status code is 200, and the content of the response is as expected.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    permissions = [
        permission_class(id=1, acl="Allow|role:admin|create"),
        permission_class(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(permissions, permission_table)

    response = client.get(f"/permissions/?permission_query={permission_query}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    assert data[0]["id"] == 1
    assert data[0]["acl"] == "Allow|role:admin|create"
    assert data[1]["id"] == 2
    assert data[1]["acl"] == "Allow|role:admin|view"


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_permissions_empty(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    Test the GET in the /permissions/ returns the list of existing Permissions even when there is none.

    We show this by making a request to the /permissions/ endpoint, asserting that the response
    status code is 200 and that the contents of the response is empty.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.get(f"/permissions/?permission_query={permission_query}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_permissions_bad_query_string(user_data, client):
    """
    Test the GET in the /permissions/ with a bad query string returns the status code 422.

    We show this by making a request to the /permissions/ endpoint with a bad query string and asserting
    that the response status code is 422.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.get("/permissions/?permission_query=app")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_permissions_without_query_string(user_data, client):
    """
    Test the GET in the /permissions/ without a query string returns the status code 422.

    We show this by making a request to the /permissions/ endpoint without a query string and asserting
    that the response status code is 422.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.get("/permissions/")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_permissions(user_data, client, permission_class, permission_table, permission_query):
    """
    Test DELETE /permissions/{id} by a superuser correctly deletes the Permission.

    This test proves that a Permission is successfully deleted via a DELETE request to the /permissions/.
    We show this this asserting that the Permission no longer exists in the database and the
    correct status code (204) is returned.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    permissions = [
        permission_class(id=1, acl="Allow|role:admin|create"),
        permission_class(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(permissions, permission_table)

    response = client.delete(f"/permissions/1?permission_query={permission_query}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 1

    permissions = [permission_class.parse_obj(x) for x in raw_permissions]
    assert permissions[0].id == 2


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_permissions_not_superuser(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    Test that is not possible for a non superuser to delete permissions.

    This test proves that is not possible for a non superuser to delete Permission.
    We show this by asserting that the return status code is 401 and the Permissions still exists
    in the database.
    """
    user = [UserCreate(is_superuser=False, **user_data)]
    await insert_objects(user, users_table)

    permissions = [
        permission_class(id=1, acl="Allow|role:admin|create"),
        permission_class(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(permissions, permission_table)

    response = client.delete(f"/permissions/1?permission_query={permission_query}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 2

    permissions = [permission_class.parse_obj(x) for x in raw_permissions]
    assert permissions[0].id == 1
    assert permissions[1].id == 2


@pytest.mark.parametrize(
    "permission_class,permission_table,permission_query",
    [(ApplicationPermission, application_permissions_table, "application")],
)
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_permissions_not_found(
    user_data, client, permission_class, permission_table, permission_query
):
    """
    Test that is not possible to delete a Permission that doesn't exists.

    This test proves that is not possible to delete a Permission that doesn't exists. We show this by
    asserting that the response status code is 404 and that the Permissions still exists in the
    database.
    """
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    permissions = [
        permission_class(id=1, acl="Allow|role:admin|create"),
        permission_class(id=2, acl="Allow|role:admin|view"),
    ]
    await insert_objects(permissions, permission_table)

    response = client.delete(f"/permissions/123?permission_query={permission_query}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    assert len(raw_permissions) == 2

    permissions = [permission_class.parse_obj(x) for x in raw_permissions]
    assert permissions[0].id == 1
    assert permissions[1].id == 2


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_permissions_bad_query_string(user_data, client):
    """
    Test the DELETE in the /permissions/ with a bad query string returns the status code 422.

    We show this by making a request to the /permissions/ endpoint with a bad query string and asserting
    that the response status code is 422.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.delete("/permissions/1?permission_query=app")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_permissions_without_query_string(user_data, client):
    """
    Test the DELETE in the /permissions/ without the query string returns the status code 422.

    We show this by making a request to the /permissions/ endpoint without a query string and asserting
    that the response status code is 422.
    """
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.delete("/permissions/1")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
