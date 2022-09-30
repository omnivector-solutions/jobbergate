"""
Test the storage module.
"""

import enum

import pytest
from sqlalchemy import Column, Enum, Integer, Table

from jobbergate_api.metadata import metadata
from jobbergate_api.storage import build_db_url, database, sort_clause


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


@pytest.mark.asyncio
async def test_sort_clause__auto_sort_enum_column(database_engine):
    """
    Provide a test case for the ``sort_clause()`` function.

    Test that the sort_clause() function will correctly sort enum columns.
    """

    class DummyStatusEnum(str, enum.Enum):
        CREATED = "CREATED"
        SUBMITTED = "SUBMITTED"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"
        UNKNOWN = "UNKNOWN"
        REJECTED = "REJECTED"

    dummy_table = Table(
        "dummies",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("status", Enum(DummyStatusEnum, sort_key_function=lambda v: str(v.value)), nullable=False),
    )
    dummy_sortables = [dummy_table.c.id, dummy_table.c.status]

    # Note: do not worry about dropping the table. The pytest fixtures will clean it up for us
    dummy_table.create(database_engine)
    await database.execute_many(
        query=dummy_table.insert(),
        values=[
            dict(id=44, status="COMPLETED"),
            dict(id=45, status="FAILED"),
            dict(id=46, status="REJECTED"),
            dict(id=47, status="COMPLETED"),
            dict(id=48, status="CREATED"),
            dict(id=49, status="SUBMITTED"),
            dict(id=50, status="REJECTED"),
            dict(id=51, status="FAILED"),
        ],
    )
    status_sort_clause = sort_clause("status", dummy_sortables, True)
    query = dummy_table.select().order_by(status_sort_clause, "id")
    results = await database.fetch_all(query)
    assert [(d["id"], d["status"]) for d in results] == [
        (44, "COMPLETED"),
        (47, "COMPLETED"),
        (48, "CREATED"),
        (45, "FAILED"),
        (51, "FAILED"),
        (46, "REJECTED"),
        (50, "REJECTED"),
        (49, "SUBMITTED"),
    ]

    status_sort_clause = sort_clause("status", dummy_sortables, False)
    query = dummy_table.select().order_by(status_sort_clause, "id")
    results = await database.fetch_all(query)
    assert [(d["id"], d["status"]) for d in results] == [
        (49, "SUBMITTED"),
        (46, "REJECTED"),
        (50, "REJECTED"),
        (45, "FAILED"),
        (51, "FAILED"),
        (48, "CREATED"),
        (44, "COMPLETED"),
        (47, "COMPLETED"),
    ]
