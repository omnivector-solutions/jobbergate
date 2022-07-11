"""
Test the storage module.
"""

from jobbergate_api.storage import build_db_url


def test_build_db_url__creates_database_url_from_parts(tweak_settings):
    """
    Provide a test ase for the ``build_db_url()`` function.

    Tests that the build_db_url function computes a database url value from separate
    DATABASE_ settings when the DEPLOY_ENV is not TEST.
    """
    with tweak_settings(
        DEPLOY_ENV="LOCAL",
        DATABASE_USER="built-base-user",
        DATABASE_PSWD="built-base-pswd",
        DATABASE_HOST="built-base-host",
        DATABASE_NAME="built-base-name",
        DATABASE_PORT=8888,
        TEST_DATABASE_USER="built-test-user",
        TEST_DATABASE_PSWD="built-test-pswd",
        TEST_DATABASE_HOST="built-test-host",
        TEST_DATABASE_NAME="built-test-name",
        TEST_DATABASE_PORT=9999,
    ):
        assert build_db_url() == (
            "postgresql://built-base-user:built-base-pswd@built-base-host:8888/built-base-name"
        )


def test_build_db_url__uses_TEST_prefixed_database_settings_if_passed_the_force_test_flag(tweak_settings):
    """
    Provide a test ase for the ``build_db_url()`` function.

    Tests that the build_db_url function computes a database url value from separate
    TEST_DATABASE_ settings when the DEPLOY_ENV is TEST.
    """
    with tweak_settings(
        DEPLOY_ENV="TEST",
        DATABASE_USER="built-base-user",
        DATABASE_PSWD="built-base-pswd",
        DATABASE_HOST="built-base-host",
        DATABASE_NAME="built-base-name",
        DATABASE_PORT=8888,
        TEST_DATABASE_USER="built-test-user",
        TEST_DATABASE_PSWD="built-test-pswd",
        TEST_DATABASE_HOST="built-test-host",
        TEST_DATABASE_NAME="built-test-name",
        TEST_DATABASE_PORT=9999,
    ):
        assert build_db_url() == (
            "postgresql://built-test-user:built-test-pswd@built-test-host:9999/built-test-name"
        )
