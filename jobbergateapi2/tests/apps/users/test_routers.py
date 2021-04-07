"""
Tests for the /users endpoint
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.users.models import User as UserModel

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.mark.asyncio
async def test_search(client):
    """
    Create a user then test if the search works
    """
    user = await UserModel.create(username="user1", email="email1@email.com", password="123")

    response = client.get(f"/users/?q={user.username}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_search_with_pagination_limit_offset(client):
    """
    Test if the pagination is working throught the endpoint with 2 users
    """
    await UserModel.create(username="user1", email="email1@email.com", password="123")
    await UserModel.create(username="user2", email="email2@email.com", password="123")

    user_name = "user1"
    response = client.get(f"/users/?q={user_name}&limit=1&offset=0")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert len(await UserModel.query.gino.all()) == 2


def test_search_without_results(client):
    """
    Test when there is no user matching the search criteria
    """
    response = client.get("/users/?name=Some Name")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_create_user(client, user_data):
    """
    Test user creation
    """
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    assert len(await UserModel.query.gino.all()) == 1
    user = await UserModel.query.gino.first()
    assert user.is_active is True
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_create_user_duplication(client, user_data):
    """
    Test the case where there is a violation in the database constraints for unique
    """
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert len(await UserModel.query.gino.all()) == 1


@pytest.mark.asyncio
async def test_create_user_admin(client, user_data):
    """
    Test creating the user with the admin permission
    """
    user_data["is_admin"] = True
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    assert len(await UserModel.query.gino.all()) == 1
    user = await UserModel.query.gino.first()
    assert user.is_active is True
    assert user.is_admin is True
