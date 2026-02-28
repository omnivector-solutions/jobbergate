"""Tests for the LDAP user mapper module."""

from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker
from ldap3 import RESTARTABLE
from ldap3.core.exceptions import LDAPSocketOpenError

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
            LDAP_DOMAIN="test.domain.com",
            LDAP_PASSWORD=faker.password(),
            LDAP_BIND_DN="cn=admin,dc=test,dc=domain,dc=com",
            LDAP_SEARCH_BASE="ou=People,dc=test,dc=domain,dc=com",
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
        mock_entry.__getitem__.side_effect = lambda x: {"uid": "testuser", "mail": "test@example.com"}[x]
        mock_conn.entries = [mock_entry]

        yield mock_conn


def test_ldap_settings_initialization(faker: Faker):
    """Test LDAPSettings initialization with environment variables."""

    env_vars = {
        "JOBBERGATE_AGENT_LDAP_DOMAIN": faker.domain_name(),
        "JOBBERGATE_AGENT_LDAP_PASSWORD": faker.password(),
        "JOBBERGATE_AGENT_LDAP_BIND_DN": f"cn=admin,dc=example,dc=com",
        "JOBBERGATE_AGENT_LDAP_SEARCH_BASE": f"ou=People,dc=example,dc=com",
    }

    with patch.dict("os.environ", env_vars):
        settings = LDAPSettings()

    assert settings.LDAP_DOMAIN == env_vars["JOBBERGATE_AGENT_LDAP_DOMAIN"]
    assert settings.LDAP_PASSWORD == env_vars["JOBBERGATE_AGENT_LDAP_PASSWORD"]
    assert settings.LDAP_BIND_DN == env_vars["JOBBERGATE_AGENT_LDAP_BIND_DN"]
    assert settings.LDAP_SEARCH_BASE == env_vars["JOBBERGATE_AGENT_LDAP_SEARCH_BASE"]


def test_ldap_settings_uid_attribute_default(faker: Faker):
    """Test that LDAP_UID_ATTRIBUTE defaults to 'uid'."""
    settings = LDAPSettings(
        LDAP_DOMAIN="example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,dc=example,dc=com",
    )
    assert settings.LDAP_UID_ATTRIBUTE == "uid"


def test_ldap_settings_uid_attribute_override(faker: Faker):
    """Test that LDAP_UID_ATTRIBUTE can be overridden."""
    settings = LDAPSettings(
        LDAP_DOMAIN="example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,dc=example,dc=com",
        LDAP_UID_ATTRIBUTE="cn",
    )
    assert settings.LDAP_UID_ATTRIBUTE == "cn"


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
        mock_ldap_connection.bind.assert_called_once()

    mock_ldap_connection.unbind.assert_called_once()


def test_ldap_connection_bind_failure(mock_ldap_settings):
    """Test LDAP connection when bind fails."""
    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn
        mock_conn.bind.return_value = False  # Bind fails

        with pytest.raises(RuntimeError, match="Couldn't bind to LDAP server"):
            with ldap_connection(mock_ldap_settings):
                pass

        # Ensure unbind is called even on failure
        mock_conn.unbind.assert_called_once()


# Tests for get_msad_user_details
def test_get_msad_user_details_success(mock_ldap_settings, mock_ldap_connection):
    """Test successful user details retrieval from LDAP."""
    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_context.return_value.__enter__.return_value = mock_ldap_connection

        result = get_msad_user_details("test@example.com", mock_ldap_settings)

        assert isinstance(result, UserDetails)
        assert result.uid == "testuser"
        assert result.email == "test@example.com"

        # Verify search was called with correct parameters
        mock_ldap_connection.search.assert_called_once_with(
            search_base="ou=People,dc=test,dc=domain,dc=com",
            search_filter="(mail=test@example.com)",
            attributes=["uid", "mail"],
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


def test_user_database_missing_with_ldap_connection_error():
    """Test UserDatabase __missing__ re-raises LDAP connection errors (transient) instead of KeyError."""
    search_function = MagicMock(side_effect=LDAPSocketOpenError("unable to open socket"))
    user_db = UserDatabase(search_missing=search_function)

    with pytest.raises(LDAPSocketOpenError):
        user_db["test@example.com"]

    search_function.assert_called_once_with("test@example.com")


def test_user_database_missing_with_unexpected_error():
    """Test UserDatabase __missing__ re-raises unexpected errors instead of converting to KeyError."""
    search_function = MagicMock(side_effect=RuntimeError("something went wrong"))
    user_db = UserDatabase(search_missing=search_function)

    with pytest.raises(RuntimeError, match="something went wrong"):
        user_db["test@example.com"]

    search_function.assert_called_once_with("test@example.com")


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
        LDAP_DOMAIN=faker.domain_name(),
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,dc=example,dc=com",
    )

    with patch("jobbergate_agent.user_mapper.ldap.Connection") as mock_conn_class:
        mock_conn = MagicMock()
        mock_conn_class.return_value = mock_conn
        mock_conn.bind.return_value = True

        with ldap_connection(settings):
            # Verify connection was created with correct parameters
            mock_conn_class.assert_called_once()
            _, kwargs = mock_conn_class.call_args

    assert kwargs["user"] == "cn=admin,dc=example,dc=com"
    assert kwargs["password"] == settings.LDAP_PASSWORD
    assert kwargs["authentication"] == "SIMPLE"
    assert kwargs["client_strategy"] == RESTARTABLE


def test_search_base_used_in_search(faker: Faker):
    """Test that LDAP_SEARCH_BASE is used directly in searches."""
    settings = LDAPSettings(
        LDAP_DOMAIN="ldap.example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,ou=org-uuid,ou=organizations,dc=example,dc=com",
    )

    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn

        # Mock successful search result
        mock_entry = MagicMock()
        mock_entry.__getitem__.side_effect = lambda x: {"uid": "testuser", "mail": "test@example.com"}[x]
        mock_conn.entries = [mock_entry]

        get_msad_user_details("test@example.com", settings)

        # Verify search was called with correct search_base
        mock_conn.search.assert_called_once()
        args, kwargs = mock_conn.search.call_args

    assert args == ()
    assert kwargs["search_base"] == "ou=People,ou=org-uuid,ou=organizations,dc=example,dc=com"


def test_search_base_explicit_override(faker: Faker):
    """Test that LDAP_SEARCH_BASE is used as the search base."""
    settings = LDAPSettings(
        LDAP_DOMAIN="openldap.dev.example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="dc=example,dc=com",
    )
    assert settings.LDAP_SEARCH_BASE == "dc=example,dc=com"


def test_uid_attribute_default(faker: Faker):
    """Test that LDAP_UID_ATTRIBUTE defaults to 'uid'."""
    settings = LDAPSettings(
        LDAP_DOMAIN="example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,dc=example,dc=com",
    )
    assert settings.LDAP_UID_ATTRIBUTE == "uid"


def test_uid_attribute_override(faker: Faker):
    """Test that LDAP_UID_ATTRIBUTE can be overridden (e.g. for MS AD)."""
    settings = LDAPSettings(
        LDAP_DOMAIN="example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="ou=People,dc=example,dc=com",
        LDAP_UID_ATTRIBUTE="cn",
    )
    assert settings.LDAP_UID_ATTRIBUTE == "cn"


def test_get_msad_user_details_with_uid_attribute(faker: Faker):
    """Test that get_msad_user_details uses the configured uid attribute."""
    settings = LDAPSettings(
        LDAP_DOMAIN="example.com",
        LDAP_PASSWORD=faker.password(),
        LDAP_BIND_DN="cn=admin,dc=example,dc=com",
        LDAP_SEARCH_BASE="dc=example,dc=com",
        LDAP_UID_ATTRIBUTE="cn",
    )

    with patch("jobbergate_agent.user_mapper.ldap.ldap_connection") as mock_context:
        mock_conn = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_conn

        mock_entry = MagicMock()
        mock_entry.__getitem__.side_effect = lambda x: {"cn": "james_example", "mail": "james@example.com"}[x]
        mock_conn.entries = [mock_entry]

        result = get_msad_user_details("james@example.com", settings)

        assert result.uid == "james_example"
        assert result.email == "james@example.com"

        mock_conn.search.assert_called_once_with(
            search_base="dc=example,dc=com",
            search_filter="(mail=james@example.com)",
            attributes=["cn", "mail"],
            size_limit=0,
        )


def test_userdatabase_close_and_del(tmp_path):
    db_path = tmp_path / "test_userdb.sqlite3"
    user_db = UserDatabase(str(db_path))
    # Add a user to ensure DB is open and in use
    user_db["test@example.com"] = "testuser"
    assert user_db["test@example.com"] == "testuser"
    # Test close method
    user_db.close()
    assert user_db.connection is None
    # Test calling close again (should not raise)
    user_db.close()
    # Test __del__ (should not raise)
    user_db.__del__()


def test_userdatabase_close_handles_exception(monkeypatch, tmp_path):
    db_path = tmp_path / "test_userdb2.sqlite3"
    user_db = UserDatabase(str(db_path))

    # Patch connection.close to raise
    class DummyConn:
        def close(self):
            raise RuntimeError("close failed")

    user_db.connection = DummyConn()
    # Should not raise
    user_db.close()
    # Should not raise
    user_db.__del__()
