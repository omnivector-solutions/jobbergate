"""
Configuration of pytest for the user resource tests
"""
import pytest


@pytest.fixture
def user_data():
    """
    Default user data for testing
    """
    return {
        "email": "user1@email.com",
        "username": "username",
        "password": "supersecret",
    }
