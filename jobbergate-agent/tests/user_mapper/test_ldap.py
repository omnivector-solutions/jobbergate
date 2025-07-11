"""Tests for the storage module."""

import pytest
from jobbergate_agent.user_mapper.ldap import UserDatabase


@pytest.fixture
def user_db():
    """Return a UserDatabase object to support the tests."""
    db = UserDatabase()
    return db


def test_set_and_get_item(user_db):
    """Test that we can set and get an item from the database."""
    email = "test@example.com"
    username = "test"
    user_db[email] = username
    assert user_db.get(email) == username


def test_set_and_get_item_key_error(user_db):
    """Test that we get a KeyError when the user does not exist in the database."""
    with pytest.raises(KeyError):
        user_db["nonexistent"]


def test_del_item(user_db):
    """Test that we can delete an item from the database."""
    username = "test"
    email = "test@example.com"
    user_db[email] = username
    del user_db[email]
    with pytest.raises(KeyError):
        user_db[email]


def test_del_item_key_error(user_db):
    """Test that we get a KeyError when the user does not exist in the database."""
    with pytest.raises(KeyError):
        del user_db["nonexistent"]


def test_iter(user_db):
    """Test that we can iterate over the usernames in the database."""
    user_db["test1@example.com"] = "test1"
    user_db["test2@example.com"] = "test2"
    assert set(user_db) == {"test1@example.com", "test2@example.com"}


def test_len(user_db):
    """Test that we can get the number of users in the database."""
    user_db["test1@example.com"] = "test1"
    user_db["test2@example.com"] = "test2"
    assert len(user_db) == 2
