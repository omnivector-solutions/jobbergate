"""This module contains the UserDatabase class."""

import sqlite3
import ssl
from collections.abc import MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Iterator

from ldap3 import RESTARTABLE, Connection, Server, Tls
from ldap3.utils.conv import escape_filter_chars
from loguru import logger
from pydantic import BaseModel, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobbergate_agent.settings import SETTINGS, _get_env_file


class LDAPSettings(BaseSettings):
    """Settings for the LDAP plugin."""

    LDAP_DOMAIN: str
    LDAP_USERNAME: str
    LDAP_PASSWORD: str
    LDAP_BIND_DN: str | None = None

    model_config = SettingsConfigDict(env_prefix="JOBBERGATE_AGENT_", env_file=_get_env_file(), extra="ignore")

    @field_validator("LDAP_DOMAIN")
    def validate_ldap_domain(cls, value: str) -> str:  # noqa: N805
        """Validate that LDAP_DOMAIN is a valid dot-separated domain name.

        Args:
            value: The LDAP_DOMAIN value to validate.

        Returns:
            str: The validated LDAP_DOMAIN value.

        Raises:
            ValueError: If LDAP_DOMAIN is empty or doesn't contain at least one dot.
        """
        if not value or not value.strip():
            raise ValueError("LDAP_DOMAIN cannot be empty")

        if "." not in value:
            raise ValueError("LDAP_DOMAIN must be a dot-separated domain name (e.g., 'example.com')")

        # Check that after splitting by dots, we have at least 2 non-empty parts
        parts = [part.strip() for part in value.split(".")]
        if len(parts) < 2 or any(not part for part in parts):
            raise ValueError(
                "LDAP_DOMAIN must be a valid dot-separated domain name with at least two parts (e.g., 'example.com')"
            )

        return value

    @property
    def search_base(self) -> str:
        """Compute the LDAP search base from the domain."""
        return ",".join(f"DC={dc}" for dc in self.LDAP_DOMAIN.split("."))

    @property
    def bind_dn(self) -> str:
        """Compute the bind DN, using LDAP_BIND_DN if set, otherwise constructing from domain and username."""
        if self.LDAP_BIND_DN:
            return self.LDAP_BIND_DN
        return f"cn={self.LDAP_USERNAME},{self.search_base}"

    @property
    def db_path(self) -> Path:
        """Property to compute the path for the local cache db based on the cache dir from jobbergate-agent."""
        return SETTINGS.CACHE_DIR / "user_mapper.sqlite3"


class UserDetails(BaseModel):
    """Base model for user details."""

    uid: str
    email: EmailStr

    @field_validator("uid", mode="before")
    def convert_to_lower(cls, value):  # noqa: N805
        """Ensure uid is in lower case."""
        return value.lower()


@contextmanager
def ldap_connection(ldap_settings: LDAPSettings) -> Iterator[Connection]:
    """Context manager that yields an LDAPS connection, closing appropriately."""
    logger.debug("Starting LDAPS connection to {}", ldap_settings.LDAP_DOMAIN)

    tls_config = Tls(validate=ssl.CERT_REQUIRED)

    server = Server(
        ldap_settings.LDAP_DOMAIN,
        port=636,
        use_ssl=True,
        tls=tls_config,
    )

    ldap_conn = Connection(
        server,
        user=ldap_settings.bind_dn,
        password=ldap_settings.LDAP_PASSWORD,
        authentication="SIMPLE",
        client_strategy=RESTARTABLE,
    )

    try:
        if not ldap_conn.bind():
            raise RuntimeError(
                f"Couldn't bind to LDAP server: {ldap_conn.result}"
            )

        logger.debug("Connected to LDAP server")
        yield ldap_conn

    finally:
        try:
            ldap_conn.unbind()
            logger.debug("Closed connection to LDAP server")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {e}")


def get_msad_user_details(email: str, ldap_settings: LDAPSettings) -> UserDetails:
    """Get user details given their uid or email."""
    search_base = ldap_settings.search_base
    search_filter = f"(mail={escape_filter_chars(email)})"

    with ldap_connection(ldap_settings) as ldap_conn:
        ldap_conn.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=["cn", "mail"],
            size_limit=0,
        )

    entries = ldap_conn.entries
    if len(entries) != 1:
        raise ValueError(
            f"Did not find exactly one match for {email=}. Found {len(entries)}",
        )

    match = entries.pop()
    try:
        uid = str(match["cn"])
        email = str(match["mail"])
        return UserDetails(uid=uid, email=email)
    except Exception as e:
        logger.debug(f"Received {match=}")
        raise ValueError(f"Failed to extract data from LDAP entry: {e}") from e


@dataclass
class UserDatabase(MutableMapping):
    """A class representing a user database where the key is the email and the value is the username.

    * It is a subclass of the MutableMapping class, so it can be used like a dictionary.
    * Since it maps emails to usernames, it is a valid ``SlurmUserMapper`` for jobbergate-agent.
    * It is powered by SQLite from the standard library, aiming to provide data persistence.

    Args:
        database (str): The path to the SQLite database file. Default is ":memory:".

    Attributes:
        connection (sqlite3.Connection): The connection to the SQLite database.
    """

    database: str = ":memory:"
    search_missing: Callable[[str], UserDetails] | None = None

    def __post_init__(self):
        """Initializes the connection to the database and create the user table."""
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.create_user_table()
        self.check_user_table()

    def create_user_table(self) -> None:
        """Creates the user table in the database if it doesn't exist."""
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user (
                    email TEXT PRIMARY KEY,
                    username TEXT
                )
                """
            )

    def check_user_table(self) -> None:
        """Checks that the user table has the expected schema."""
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        expected_columns = [("email", "TEXT"), ("username", "TEXT")]
        actual_columns = [(column[1], column[2]) for column in columns]
        if actual_columns != expected_columns:
            raise ValueError(
                f"Table schema does not match expected schema. Actual: {actual_columns}, Expected: {expected_columns}"
            )

    def __getitem__(self, email: str) -> str:
        """Retrieves the username of a user given their email.

        Args:
            email (str): The email of the user.

        Returns:
            str: The username of the user.

        Raises:
            KeyError: If the user does not exist in the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT username FROM user WHERE email=?", (email,))
        row = cursor.fetchone()
        if row is None:
            return self.__missing__(email)
        return row["username"]

    def __missing__(self, email: str) -> str:
        """Looks on the LDAP server if the email is not found.

        Args:
            email (str): The email of the user.

        Returns:
            str: The username of the user, derived from the email.
        """
        if self.search_missing is not None:
            try:
                user_details = self.search_missing(email)
            except ValueError as e:
                logger.error(f"User not found in LDAP for email {email}: {e}")
                raise KeyError(email) from e
            self[email] = user_details.uid
            return user_details.uid
        raise KeyError(email)

    def __setitem__(self, email: str, username: str) -> None:
        """Inserts or updates a user in the database.

        Args:
            email (str): The email address of the user.
            username (str): The username of the user.
        """
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO user(email,username) VALUES (?, ?)",
                (email, username),
            )

    def __delitem__(self, email: str) -> None:
        """Deletes a user from the database.

        Args:
            email (str): The email of the user.

        Raises:
            KeyError: If the user does not exist in the database.
        """
        if email not in self:
            raise KeyError(email)
        with self.connection:
            self.connection.execute("DELETE FROM user WHERE email=?", (email,))

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the emails in the database.

        Returns:
            Iterator[str]: An iterator over the emails.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT email FROM user")
        return (row["email"] for row in cursor.fetchall())

    def __len__(self) -> int:
        """Returns the number of users in the database.

        Returns:
            int: The number of users in the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM user")
        return cursor.fetchone()[0]

    def close(self) -> None:
        """Close the underlying database connection, if it is open."""
        connection = getattr(self, "connection", None)
        if connection is None:
            return
        try:
            connection.close()
        except Exception as exc:  # pragma: no cover - defensive cleanup
            logger.warning(f"Error while closing UserDatabase connection: {exc}")
        finally:
            self.connection = None  # type: ignore[assignment]

    def __del__(self) -> None:
        """Ensure the database connection is closed when the instance is garbage collected."""
        try:
            self.close()
        except Exception:
            # Avoid raising exceptions during object finalization
            pass


def user_mapper_factory() -> UserDatabase:
    """User mapper factory to be used by jobbergate-agent using the cache database."""
    ldap_settings = LDAPSettings()  # type: ignore[call-arg]
    ldap_settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    user_mapper = UserDatabase(
        ldap_settings.db_path.as_posix(),
        search_missing=partial(get_msad_user_details, ldap_settings=ldap_settings),
    )
    return user_mapper

