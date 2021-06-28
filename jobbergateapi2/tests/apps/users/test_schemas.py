"""
Test the schema of the resource User
"""
import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.users.schemas import _PRINCIPALS_RX, User, UserCreate


def test_principals_regex():
    """
    Assert the principal validation regex.
    """
    assert _PRINCIPALS_RX == r"^(role:\w+)?(\|role:\w+)*$"


def test_create_user_missing_required_atribute(user_data):
    """
    Test that a ValidationError is raised when creating a user without a required attribute.
    """
    user_data.pop("email")

    with pytest.raises(ValidationError):
        User(**user_data)


def test_create_user_with_invalid_email(user_data):
    """
    Test that a ValidationError is raised when an invalid email address is supplied.
    """
    user_data["email"] = "email"

    with pytest.raises(ValidationError) as exc:
        UserCreate(**user_data)

    assert "value is not a valid email address" in str(exc)


def test_create_user_with_invalid_password_length(user_data):
    """
    Test that a ValidationError is raised when a password length < 12 chars is used.
    """
    user_data["password"] = "00123456789"

    with pytest.raises(ValidationError) as exc:
        UserCreate(**user_data)

    assert "ensure this value has at least 12 characters" in str(exc)


@pytest.mark.parametrize(
    "principals",
    [
        ("|"),
        ("role"),
        ("role:admin|"),
        ("roleadmin|"),
    ],
)
def test_create_user_with_invalid_principals(user_data, principals):
    """
    Test that a ValidationError is raised when an invalid principals format is supplied.
    """
    user_data["principals"] = principals

    with pytest.raises(ValidationError):
        UserCreate(**user_data)


def test_user_string_conversion(user_data):
    """
    Check if the string representation of the User resource is correct.
    """
    user = User(**user_data)

    expected_str = f"{user.id}, {user.full_name}, {user.email}"

    assert str(user) == expected_str


def test_create_user(user_data):
    """
    Check if the user creation works.
    """
    user = User(**user_data)

    assert user.email == user_data["email"]
    assert user.is_superuser is False
    assert user.full_name == user_data["full_name"]
    assert user.Config.orm_mode is True


@pytest.mark.parametrize(
    "principals",
    [
        (""),
        ("role:admin"),
        ("role:admin|role:operator"),
    ],
)
def test_create_user_principals(user_data, principals):
    """
    Check if the user creation works using the principals.
    """
    user_data["principals"] = principals
    user = User(**user_data)

    assert user.principals == principals


def test_user_hash_password(user_data):
    """
    Test if the hash_password returns.
    """
    user = UserCreate(**user_data)

    assert user.hash_password()


def test_user_hash_password_maximum_size(user_data):
    """
    Check if the hash_password works with the maximum password size.
    """
    user_data["password"] = "a" * 100
    user = UserCreate(**user_data)

    assert user.hash_password()
    assert len(user.hash_password()) <= 248


def test_user_hash_password_without_password_filled(user_data):
    """
    When creating a user, if there is no password, the hash_password can't hash it.
    """
    user_data.pop("password")

    user = UserCreate(**user_data)

    assert user.hash_password() is None
