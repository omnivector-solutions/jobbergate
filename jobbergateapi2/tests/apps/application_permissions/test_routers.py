from unittest import mock

import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.application_permissions.models import application_permissions_table
from jobbergateapi2.apps.application_permissions.routers import check_acl_string
from jobbergateapi2.apps.application_permissions.schemas import ApplicationPermission
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


@pytest.mark.parametrize(
    "string,expected",
    [
        ("Allow|role:admin|view", True),
        ("Deny|role:some_role|create", True),
        ("Deny|role|update", False),
        ("Deny", False),
        ("Allow|update", False),
        ("Allow|role:admin", False),
        ("Allow|admin|view|", False),
        ("Allow|role:admin|view|", False),
    ]
)
def test_check_acl_string(string, expected):
    assert check_acl_string(string) is expected


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions(user_data, client):
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    acl = {"acl": "Allow|role:admin|view"}
    response = client.post("/application-permissions/", data=acl)
    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 1

    query = application_permissions_table.select(application_permissions_table.c.id == 1)
    permission = ApplicationPermission.parse_obj(await database.fetch_one(query))

    assert permission is not None
    assert permission.acl == acl["acl"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions_duplicated(user_data, client):
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
    user = [UserCreate(is_superuser=False, **user_data)]
    await insert_objects(user, users_table)

    response = client.post("/application-permissions/", data={"acl": "Allow|role:admin|view"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_application_permissions_invalid_acl(user_data, client):
    user = [UserCreate(is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    response = client.post("/application-permissions/", data={"acl": "Allow|"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    count = await database.fetch_all("SELECT COUNT(*) FROM application_permissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_application_permissions(user_data, client):
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
    user = [UserCreate(**user_data)]
    await insert_objects(user, users_table)

    response = client.get("/application-permissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_permissions(user_data, client):
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


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_application_permissions_not_superuser(user_data, client):
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
