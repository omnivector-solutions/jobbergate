"""
Tests for the /users endpoint.
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import User, UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_single_element(client, user_data):
    """
    Create a user then test if the listing works.
    """

    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/users/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1

    assert data[0]["id"] == 1
    assert data[0]["full_name"] == user_data["full_name"]
    assert data[0]["email"] == user_data["email"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_multiple_elements(client, user_data):
    """
    Create multiple users then test if the listing works.
    """

    users = [
        UserCreate(full_name="user1", email="email1@email.com", password="1" * 12),
        UserCreate(full_name="user2", email="email2@email.com", password="1" * 12),
    ]
    await insert_objects(users, users_table)

    response = client.get("/users/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    assert data[0]["id"] == 1
    assert data[0]["email"] == "email1@email.com"
    assert data[1]["id"] == 2
    assert data[1]["email"] == "email2@email.com"


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_with_pagination_limit_1_offset_0(client):
    """
    Test if the pagination is working through the endpoint using offset=0 and limit=1
    """
    users = [
        UserCreate(full_name="user1", email="email1@email.com", password="1" * 12),
        UserCreate(full_name="user2", email="email2@email.com", password="1" * 12),
    ]
    await insert_objects(users, users_table)

    response = client.get("/users/?limit=1&skip=0")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["email"] == "email1@email.com"


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_with_pagination_limit_1_offset_1(client):
    """
    Test if the pagination is working through the endpoint using offset=1 and limit=1
    """
    users = [
        UserCreate(full_name="user1", email="email1@email.com", password="1" * 12),
        UserCreate(full_name="user2", email="email2@email.com", password="1" * 12),
    ]
    await insert_objects(users, users_table)

    response = client.get("/users/?limit=1&skip=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 2
    assert data[0]["email"] == "email2@email.com"


@pytest.mark.asyncio
async def test_list_without_results(client):
    """
    Test listing when no users exist to list.
    """
    response = client.get("/users/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_user(client, user_data):
    """
    Test create user.
    The default behavior is for the created user to be active and be not a superuser.
    """
    response = client.post("/users/", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    count = await database.fetch_all("SELECT COUNT(*) FROM users")
    assert count[0][0] == 1

    user = User.parse_obj(await database.fetch_one(users_table.select()))
    assert user.is_superuser is False
    assert user.is_active is True


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_user_duplication(client, user_data):
    """
    Test the case where there is a violation in the database constraints for unique.
    """
    response = client.post("/users/", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    response = client.post("/users/", json=user_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    count = await database.fetch_all("SELECT COUNT(*) FROM users")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_superuser(client, user_data):
    """
    Test create a superuser.
    """
    user_data["is_superuser"] = True
    response = client.post("/users/", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    count = await database.fetch_all("SELECT COUNT(*) FROM users")
    assert count[0][0] == 1

    user = User.parse_obj(await database.fetch_one(users_table.select()))
    assert user.is_superuser is True


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_users_get(client, user_data):
    """
    Test getting a user by id.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/users/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_users_get_empty(client):
    """
    Try to get the user of id=1 which doesn't exists and will return 404.
    """
    response = client.get("/users/1")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_users_me(client, user_data):
    """
    Test the /user/me endpoint, should return the current authenticated user.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/user/me")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_user(client, user_data):
    """
    Test update an User.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.put("/users/1", json={"full_name": "new name"})

    assert response.status_code == status.HTTP_201_CREATED

    query = users_table.select(users_table.c.id == 1)
    user = User.parse_obj(await database.fetch_one(query))

    assert user is not None
    assert user.full_name == "new name"


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_user_superuser(client, user_data):
    """
    Test update an User to change the superuser status.
    """
    user = [UserCreate(id=1, is_superuser=True, **user_data)]
    await insert_objects(user, users_table)

    response = client.put("/users/1", json={"is_superuser": False})

    assert response.status_code == status.HTTP_201_CREATED

    query = users_table.select(users_table.c.id == 1)
    user = User.parse_obj(await database.fetch_one(query))

    assert user is not None
    assert user.is_superuser is False


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_user_not_found(client, user_data):
    """
    Try to update a User not found, must return 404 and do nothing with the stored data.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.put("/users/123", json={"full_name": "new name"})

    assert response.status_code == status.HTTP_404_NOT_FOUND

    query = users_table.select(users_table.c.id == 1)
    user = User.parse_obj(await database.fetch_one(query))

    assert user is not None
    assert user.full_name == user_data["full_name"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_user_me(client, user_data):
    """
    Test update the authenticated User.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.put("/user/me", json={"full_name": "new name"})

    assert response.status_code == status.HTTP_201_CREATED

    query = users_table.select(users_table.c.id == 1)
    user = User.parse_obj(await database.fetch_one(query))

    assert user is not None
    assert user.full_name == "new name"
