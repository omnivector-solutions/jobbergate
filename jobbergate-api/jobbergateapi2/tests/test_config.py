import os
from unittest import mock

import pytest

from jobbergateapi2.config import Settings


def test_calucalte_db_url__url_escapes_existing_DATABASE_URL_setting():
    """
    Tests that the Settings object will urlencode an DATABASE_URL existing value to make it url safe.
    """

    db_settings = dict(DATABASE_URL="postgresql://test-user:test@pswd@test-host:9999/test-name")

    with mock.patch.dict(os.environ, db_settings):
        test_settings = Settings()
        assert test_settings.DATABASE_URL == "postgresql://test-user:test%40pswd@test-host:9999/test-name"


def test_calucalte_db_url__creates_database_url_from_parts():
    """
    Tests that the Settings object will compute a DATABASE_URL value from separate
    DATABASE_ settings if no DATABASE_URL is provided
    """

    db_settings = dict(
        DATABASE_USER="test-user",
        DATABASE_PSWD="test-pswd",
        DATABASE_HOST="test-host",
        DATABASE_PORT="9999",
        DATABASE_NAME="test-name",
        DATABASE_URL="",
    )

    with mock.patch.dict(os.environ, db_settings):
        test_settings = Settings()
        assert test_settings.DATABASE_URL == "postgresql://test-user:test-pswd@test-host:9999/test-name"


def test_calucalte_db_url__raises_exception_if_any_part_is_missing():
    """
    Tests that the Settings object will raise an exception when constructing a
    DATABASE_URL from separate DATABASE_ settings if no DATABASE_URL is provided.
    """

    db_settings = dict(
        DATABASE_USER="test-user", DATABASE_HOST="test-host", DATABASE_PORT="9999", DATABASE_URL="",
    )

    with mock.patch.dict(os.environ, db_settings):
        with pytest.raises(
            ValueError, match="Missing required database settings: DATABASE_NAME, DATABASE_PSWD",
        ):
            Settings()
