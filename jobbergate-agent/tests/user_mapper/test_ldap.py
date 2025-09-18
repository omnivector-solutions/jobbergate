"""Tests for the LDAP user mapper module."""

from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker
from ldap3 import NTLM, RESTARTABLE

from jobbergate_agent.user_mapper.ldap import (
    LDAPSettings,
    UserDatabase,
    UserDetails,
    get_msad_user_details,
    ldap_connection,
    user_mapper_factory,
)


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


@pytest.fixture
def mock_ldap_settings(faker: Faker, tmp_path: Path) -> Iterator[LDAPSettings]:
    """Mock LDAP settings for testing."""
    with patch("jobbergate_agent.user_mapper.ldap.SETTINGS") as mock_settings:
        mock_settings.CACHE_DIR = tmp_path
        settings = LDAPSettings(
            LDAP_DOMAIN="test.domain.com", LDAP_USERNAME=faker.user_name(), LDAP_PASSWORD=faker.password()
        )
        yield settings


@pytest.fixture
def mock_ldap_connection():
    """Mock LDAP connection for testing."""
    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn

        # Mock successful TLS and bind
        mock_conn.start_tls.return_value = True
        mock_conn.bind.return_value = True
        mock_conn.unbind.return_value = True

        # Mock search results
        mock_entry = MagicMock()
        mock_entry.__getitem__.side_effect = lambda x: {"cn": "testuser", "mail": "test@example.com"}[x]
        mock_conn.entries = [mock_entry]

        yield mock_conn


def test_ldap_settings_initialization(faker: Faker):
    """Test LDAPSettings initialization with environment variables."""

    env_vars = {
        "JOBBERGATE_AGENT_LDAP_DOMAIN": faker.domain_name(),
        "JOBBERGATE_AGENT_LDAP_USERNAME": faker.user_name(),
        "JOBBERGATE_AGENT_LDAP_PASSWORD": faker.password(),
    }

    with patch.dict("os.environ", env_vars):
        settings = LDAPSettings()

    assert settings.LDAP_DOMAIN == env_vars["JOBBERGATE_AGENT_LDAP_DOMAIN"]
    assert settings.LDAP_USERNAME == env_vars["JOBBERGATE_AGENT_LDAP_USERNAME"]
    assert settings.LDAP_PASSWORD == env_vars["JOBBERGATE_AGENT_LDAP_PASSWORD"]


def test_ldap_settings_db_path_property(mock_ldap_settings):
    """Test that db_path property returns correct path."""
    # The path will be constructed based on the actual SETTINGS.CACHE_DIR
    # so we just verify it ends with the expected filename
    assert mock_ldap_settings.db_path.name == "user_mapper.sqlite3"
    assert str(mock_ldap_settings.db_path).endswith("user_mapper.sqlite3")


def test_user_details_creation():
    """Test UserDetails model creation."""
    user_details = UserDetails(uid="TestUser", email="test@example.com")
    assert user_details.uid == "testuser"  # Should be lowercased
    assert user_details.email == "test@example.com"


def test_user_details_uid_lowercase_conversion():
    """Test that uid is automatically converted to lowercase."""
    user_details = UserDetails(uid="TESTUSER", email="test@example.com")
    assert user_details.uid == "testuser"


def test_user_details_invalid_email():
    """Test that invalid email raises validation error."""
    with pytest.raises(ValueError):
        UserDetails(uid="testuser", email="invalid-email")


def test_ldap_connection_success(mock_ldap_settings, mock_ldap_connection):
    """Test successful LDAP connection context manager."""
    with ldap_connection(mock_ldap_settings) as conn:
        assert conn is not None
        mock_ldap_connection.start_tls.assert_called_once()
        mock_ldap_connection.bind.assert_called_once()

    mock_ldap_connection.unbind.assert_called_once()


def test_ldap_connection_tls_failure(mock_ldap_settings):
    """Test LDAP connection when TLS fails."""
    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn
        mock_conn.start_tls.side_effect = Exception("TLS failed")

        with pytest.raises(Exception, match="TLS failed"):
            with ldap_connection(mock_ldap_settings):
                # no operation needed, just testing context manager
                pass

        # Ensure unbind is called even on failure
        mock_conn.unbind.assert_called_once()


def test_ldap_connection_bind_failure(mock_ldap_settings):
    """Test LDAP connection when bind fails."""
    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn
        mock_conn.start_tls.return_value = True
        mock_conn.bind.return_value = False  # Bind fails

        with pytest.raises(RuntimeError, match="Couldn't open a connection to MSAD"):
            with ldap_connection(mock_ldap_settings):
                # no operation needed, just testing context manager
                pass

        # Ensure unbind is called even on failure
        mock_conn.unbind.assert_called_once()


# Tests for get_msad_user_details
def test_get_msad_user_details_success(mock_ldap_settings, mock_ldap_connection):
    """Test successful user details retrieval from MSAD."""
    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_context.return_value.__enter__.return_value = mock_ldap_connection

        result = get_msad_user_details("test@example.com", mock_ldap_settings)

        assert isinstance(result, UserDetails)
        assert result.uid == "testuser"
        assert result.email == "test@example.com"

        # Verify search was called with correct parameters
        mock_ldap_connection.search.assert_called_once_with(
            search_base="DC=test,DC=domain,DC=com",
            search_filter="(mail=test@example.com)",
            attributes=["cn", "mail"],
            size_limit=0,
        )


def test_get_msad_user_details_no_results(mock_ldap_settings):
    """Test when no user is found in MSAD."""
    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn
        mock_conn.entries = []  # No results

        with pytest.raises(ValueError, match="Did not find exactly one match"):
            get_msad_user_details("nonexistent@example.com", mock_ldap_settings)


def test_get_msad_user_details_multiple_results(mock_ldap_settings):
    """Test when multiple users are found in MSAD."""
    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn
        mock_conn.entries = [MagicMock(), MagicMock()]  # Multiple results

        with pytest.raises(ValueError, match="Did not find exactly one match"):
            get_msad_user_details("duplicate@example.com", mock_ldap_settings)


def test_get_msad_user_details_data_extraction_error(mock_ldap_settings):
    """Test when data extraction from MSAD entry fails."""
    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn

        # Mock entry that raises exception when accessed
        mock_entry = MagicMock()
        mock_entry.__getitem__.side_effect = KeyError("cn")
        mock_conn.entries = [mock_entry]

        with pytest.raises(ValueError, match="Failed to extract data"):
            get_msad_user_details("test@example.com", mock_ldap_settings)


# Tests for UserDatabase with LDAP integration
def test_user_database_missing_with_ldap_success():
    """Test UserDatabase __missing__ method with successful LDAP lookup."""
    search_function = MagicMock(return_value=UserDetails(uid="testuser", email="test@example.com"))
    user_db = UserDatabase(search_missing=search_function)

    # Access non-existent user should trigger LDAP lookup
    result = user_db["test@example.com"]

    assert result == "testuser"
    search_function.assert_called_once_with("test@example.com")

    # Verify user was cached in database
    assert user_db["test@example.com"] == "testuser"


def test_user_database_missing_with_ldap_failure():
    """Test UserDatabase __missing__ method with LDAP lookup failure."""
    search_function = MagicMock(side_effect=ValueError("User not found"))
    user_db = UserDatabase(search_missing=search_function)

    with pytest.raises(KeyError):
        user_db["nonexistent@example.com"]

    search_function.assert_called_once_with("nonexistent@example.com")


def test_user_database_missing_without_ldap():
    """Test UserDatabase __missing__ method without LDAP search function."""
    user_db = UserDatabase(search_missing=None)

    with pytest.raises(KeyError):
        user_db["test@example.com"]


# Tests for user_mapper_factory
@patch("jobbergate_agent.user_mapper.ldap.LDAPSettings")
def test_user_mapper_factory_success(mock_ldap_settings_class, tmp_path):
    """Test successful user mapper factory creation."""
    mock_settings = MagicMock()
    mock_db_path = MagicMock()
    test_db_path = tmp_path / "user_mapper.sqlite3"
    mock_db_path.as_posix.return_value = str(test_db_path)
    mock_settings.db_path = mock_db_path
    mock_ldap_settings_class.return_value = mock_settings

    result = user_mapper_factory()

    assert isinstance(result, UserDatabase)
    assert result.database == str(test_db_path)
    assert result.search_missing is not None
    mock_db_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)


@patch("jobbergate_agent.user_mapper.ldap.LDAPSettings")
def test_user_mapper_factory_with_ldap_integration(mock_ldap_settings_class, tmp_path):
    """Test user mapper factory with LDAP integration."""
    mock_settings = MagicMock()
    mock_db_path = MagicMock()
    test_db_path = tmp_path / "user_mapper.sqlite3"
    mock_db_path.as_posix.return_value = str(test_db_path)
    mock_settings.db_path = mock_db_path
    mock_ldap_settings_class.return_value = mock_settings

    with patch("jobbergate_agent.user_mapper.ldap.get_msad_user_details") as mock_get_details:
        mock_get_details.return_value = UserDetails(uid="testuser", email="test@example.com")

        user_mapper = user_mapper_factory()

        # Test that LDAP lookup works through the factory-created mapper
        result = user_mapper["test@example.com"]
        assert result == "testuser"


# Additional integration tests
def test_ldap_connection_with_real_connection_parameters(faker: Faker):
    """Test LDAP connection context manager with realistic parameters."""
    settings = LDAPSettings(
        LDAP_DOMAIN=faker.domain_name(), LDAP_USERNAME=faker.user_name(), LDAP_PASSWORD=faker.password()
    )

    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn
        mock_conn.start_tls.return_value = True
        mock_conn.bind.return_value = True

        with ldap_connection(settings):
            # Verify connection was created with correct parameters
            mock_conn_class.assert_called_once()
            args, kwargs = mock_conn_class.call_args

    assert args == ()
    assert kwargs["server"] == settings.LDAP_DOMAIN
    assert kwargs["user"] == f"{settings.LDAP_DOMAIN}\\{settings.LDAP_USERNAME}"
    assert kwargs["password"] == settings.LDAP_PASSWORD
    assert kwargs["authentication"] == NTLM
    assert kwargs["auto_bind"] == "NONE"
    assert kwargs["client_strategy"] == RESTARTABLE


def test_search_base_construction(faker: Faker):
    """Test that search base is correctly constructed from domain."""
    settings = LDAPSettings(LDAP_DOMAIN="test.sub.domain.com", LDAP_USERNAME="testuser", LDAP_PASSWORD=faker.password())

    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn

        # Mock successful search result
        mock_entry = MagicMock()
        mock_entry.__getitem__.side_effect = lambda x: {"cn": "testuser", "mail": "test@example.com"}[x]
        mock_conn.entries = [mock_entry]

        get_msad_user_details("test@example.com", settings)

        # Verify search was called with correct search_base
        mock_conn.search.assert_called_once()
        args, kwargs = mock_conn.search.call_args

    assert args == ()
    assert kwargs["search_base"] == "DC=test,DC=sub,DC=domain,DC=com"
