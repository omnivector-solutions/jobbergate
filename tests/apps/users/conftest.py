import pytest


@pytest.fixture
def user_data():
    return {
        "email": "user1@email.com",
        "username": "username",
        "password": "supersecret",
    }
