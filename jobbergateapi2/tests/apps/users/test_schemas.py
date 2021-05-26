"""
Test the schema of the resource User
"""
import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.users.schemas import User, UserCreate


def test_create_user_missing_required_atribute(user_data):
    """
    Must raise a ValidationError when creating a user without any required attribute
    """
    user_data.pop("email")

    with pytest.raises(ValidationError):
        User(**user_data)


def test_create_user_with_invalid_email(user_data):
    """
    Must raise a ValidationError for invalid email address
    """
    user_data["email"] = "email"

    with pytest.raises(ValidationError) as exc:
        UserCreate(**user_data)

    assert "value is not a valid email address" in str(exc)


def test_create_user_with_invalid_password_length(user_data):
    """
    Must not allow small passwords
    """
    user_data["password"] = "1"

    with pytest.raises(ValidationError) as exc:
        UserCreate(**user_data)

    assert "ensure this value has at least 12 characters" in str(exc)


def test_user_string_conversion(user_data):
    """
    Check if the string representation of the User resource is correct
    """
    user = User(**user_data)

    expected_str = f"{user.id}, {user.full_name}, {user.email}"

    assert str(user) == expected_str


def test_create_user(user_data):
    """
    Check if the user creation works
    """
    user = User(**user_data)

    assert user.email == user_data["email"]
    assert user.is_superuser is False
    assert user.full_name == user_data["full_name"]
    assert user.Config.orm_mode is True


def test_user_hash_password(user_data):
    """
    Test if the hash_password returns
    """
    user = UserCreate(**user_data)

    assert user.hash_password()


def test_user_hash_password_maximum_size(user_data):
    """
    Check if the hash_password works with the maximum password size
    """
    user_data["password"] = "a" * 100
    user = UserCreate(**user_data)

    assert user.hash_password()
    assert len(user.hash_password()) <= 248


def test_user_hash_password_without_password_filled(user_data):
    """
    When creating a user, if there is no password, the hash_password can't hash it
    """
    user_data.pop("password")

    user = UserCreate(**user_data)

    assert user.hash_password() is None
