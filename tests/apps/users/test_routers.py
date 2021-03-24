import uuid

import nest_asyncio
import pytest
from fastapi import status

from .factories import UserFactory
from jobbergate_api.apps.users.models import User as UserModel

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_search(client, user_data):
    user = await UserFactory.create()

    response = client.get(f"/users/?q={user.username}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_search_with_pagination_limit_offset(client, user_data):
    await UserFactory.create()
    await UserFactory.create(**user_data)

    user_name = user_data["username"]
    response = client.get(f"/users/?q={user_name}&limit=1&offset=0")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert len(await UserModel.query.gino.all()) == 2


def test_search_without_results(client):
    response = client.get("/users/?name=Some Name")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 0


@pytest.mark.asyncio
async def test_create_user(client, user_data):
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    assert len(await UserModel.query.gino.all()) == 1
    user = await UserModel.query.gino.first()
    assert user.is_active is True
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_create_user_duplication(client, user_data):
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert len(await UserModel.query.gino.all()) == 1


@pytest.mark.asyncio
async def test_create_user_admin(client, user_data):
    user_data["is_admin"] = True
    response = client.post("/users", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    assert len(await UserModel.query.gino.all()) == 1
    user = await UserModel.query.gino.first()
    assert user.is_active is True
    assert user.is_admin is True
