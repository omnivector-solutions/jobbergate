"""
Test for the authentication endpoint: /token
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.storage import database

nest_asyncio.apply()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_payload",
    [
        {"username": "name", "password": "invalid-password"},
        {"username": "invalid-name", "password": "abc123"},
    ],
)
@database.transaction(force_rollback=True)
async def test_token_invalid_data(data_payload, client):
    """
    Test the token creation with wrong password or username, must fail
    """
    client.post("/users", json=data_payload)
    response = client.post("/token", data=data_payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Incorrect username or password"}


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_token_success_creation(client, user_data):
    """
    Test token creation with valid credentials
    """
    client.post("/users", json=user_data)
    response = client.post("/token", data={"username": "username", "password": "supersecret123456"})

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json().keys()
