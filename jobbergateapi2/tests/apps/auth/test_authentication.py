"""
Tests for the authentication process
"""
from collections import namedtuple
from unittest.mock import patch

import nest_asyncio
import pytest
from fastapi import HTTPException
from jose import jwt

from jobbergateapi2.apps.auth.authentication import Token, authenticate_user, validate_token
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.config import settings
from jobbergateapi2.storage import database

nest_asyncio.apply()


def test_validate_token():
    """
    Test if the token is able to be validated
    """
    encoded_jwt = jwt.encode({"sub": "username"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert validate_token(encoded_jwt) == "username"


def test_invalid_token():
    """
    Must raise a HTTPException when the token is invalid
    """
    encoded_jwt = jwt.encode({"sub": "username"}, "invalid_secret_key", algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exinfo:
        assert validate_token(encoded_jwt) is None
    assert exinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
@patch("jobbergateapi2.apps.auth.authentication.jwt.encode")
async def test_token_creation(mock_encode, client, user_data):
    """
    Check if the token creation works
    """
    mock_encode.return_value = "mock_hash"
    client.post("/users/", json=user_data)
    new_user = await database.fetch_one(users_table.select())

    token = Token(new_user)
    assert token.create() == {"access_token": "mock_hash", "token_type": "bearer"}


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_authenticate_user(client, user_data):
    """
    Test that after a user is created, its credentials works for authentication
    """
    client.post("/users/", json=user_data)

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock(user_data["email"], user_data["password"])
    user = await authenticate_user(form_data)
    new_user = User.parse_obj(await database.fetch_one(users_table.select()))

    assert user.id == new_user.id


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_authenticate_user_invalid_password(client, user_data):
    """
    Test with an created user, when we try a wrong password, then the auth must fail with HTTPException
    """
    client.post("/users/", json=user_data)

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock("username", "abc123")
    with pytest.raises(HTTPException) as exinfo:
        await authenticate_user(form_data)
    assert "Incorrect username or password" == exinfo.value.detail


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_authenticate_user_invalid_username(client, user_data):
    """
    Same as before, but now with a wrong username and correct password
    """
    client.post("/users/", json=user_data)

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock("username", "abc123")
    with pytest.raises(HTTPException) as exinfo:
        await authenticate_user(form_data)
    assert "Incorrect username or password" == exinfo.value.detail
