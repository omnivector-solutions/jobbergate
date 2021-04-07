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
from jobbergateapi2.apps.users.models import User as UserModel
from jobbergateapi2.apps.users.schemas import pwd_context
from jobbergateapi2.config import settings

nest_asyncio.apply()


def test_validate_token():
    """
    Test if the token is able to be validated
    """
    encoded_jwt = jwt.encode({"sub": "username"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert validate_token(encoded_jwt) is None


def test_invalid_token():
    """
    Must raise a HTTPException when the token is invalid
    """
    encoded_jwt = jwt.encode({"sub": "username"}, "invalid_secret_key", algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exinfo:
        assert validate_token(encoded_jwt) is None
    assert exinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
@patch("jobbergateapi2.apps.auth.authentication.jwt.encode")
async def test_token_creation(mock_encode, client):
    """
    Check if the token creation works
    """
    mock_encode.return_value = "mock_hash"
    password_hash = pwd_context.hash("abc123")
    new_user = await UserModel.create(username="username", password=password_hash, email="email@email.com")
    token = Token(new_user)
    assert token.create() == {"access_token": "mock_hash", "token_type": "bearer"}


@pytest.mark.asyncio
async def test_authenticate_user(client):
    """
    Test that after a user is created, its credentials works for authentication
    """
    password_hash = pwd_context.hash("abc123")
    new_user = await UserModel.create(username="username", password=password_hash, email="email@email.com")

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock("username", "abc123")
    user = await authenticate_user(form_data)
    assert user.id == new_user.id


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(client):
    """
    Test with an created user, when we try a wrong password, then the auth must fail with HTTPException
    """
    await UserModel.create(username="username", password="unhased-password", email="email@email.com")

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock("username", "abc123")
    with pytest.raises(HTTPException) as exinfo:
        await authenticate_user(form_data)
    assert "Incorrect username or password" == exinfo.value.detail


@pytest.mark.asyncio
async def test_authenticate_user_invalid_username(client):
    """
    Same as before, but now with a wrong username and correct password
    """
    password_hash = pwd_context.hash("abc123")
    await UserModel.create(username="name", password=password_hash, email="email@email.com")

    RequestFormMock = namedtuple("OAuth2PasswordRequestForm", ["username", "password"])
    form_data = RequestFormMock("username", "abc123")
    with pytest.raises(HTTPException) as exinfo:
        await authenticate_user(form_data)
    assert "Incorrect username or password" == exinfo.value.detail
