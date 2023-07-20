"""
Test the storage module.
"""

import json
import enum

import asyncpg
import pytest
from sqlalchemy import Enum, select
from sqlalchemy.orm import Mapped, mapped_column

from jobbergate_api.apps.models import Base, CommonMixin, IdMixin
from jobbergate_api.storage import build_db_url, sort_clause, handle_fk_error


class DummyStatusEnum(str, enum.Enum):
    """
    A dummy enum used to test sorting logic with enums.
    """

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


class DummySortTable(CommonMixin, IdMixin, Base):
    """
    A dummy table to test sorting logic.
    """

    status: Mapped[DummyStatusEnum] = mapped_column(Enum(DummyStatusEnum, native_enum=False), nullable=False)

    @classmethod
    def sortable_fields(cls):
        return [
            cls.id,
            cls.status,
        ]


@pytest.fixture
def insert_dummy_rows(synth_session):
    async def _helper(*rows: dict):
        instances = []
        for row in rows:
            instance = DummySortTable(**row)
            synth_session.add(instance)
            instances.append(instance)
        await synth_session.flush()
        return instances

    return _helper


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
            "postgresql+asyncpg://built-base-user:built-base-pswd@built-base-host:8888/built-base-name"
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
        assert build_db_url(force_test=True) == (
            "postgresql+asyncpg://built-test-user:built-test-pswd@built-test-host:9999/built-test-name"
        )


async def test_sort_clause__auto_sort_enum_column(synth_session, insert_dummy_rows):
    """
    Provide a test case for the ``sort_clause()`` function.

    Test that the sort_clause() function will correctly sort enum columns.
    """

    await insert_dummy_rows(
        dict(id=44, status="COMPLETED"),
        dict(id=45, status="FAILED"),
        dict(id=46, status="REJECTED"),
        dict(id=47, status="COMPLETED"),
        dict(id=48, status="CREATED"),
        dict(id=49, status="SUBMITTED"),
        dict(id=50, status="REJECTED"),
        dict(id=51, status="FAILED"),
    )
    status_sort_clause = sort_clause("status", DummySortTable.sortable_fields(), True)
    query = select(DummySortTable).order_by(status_sort_clause, "id")
    result = await synth_session.scalars(query)
    assert [(d.id, d.status) for d in result.all()] == [
        (44, DummyStatusEnum.COMPLETED),
        (47, DummyStatusEnum.COMPLETED),
        (48, DummyStatusEnum.CREATED),
        (45, DummyStatusEnum.FAILED),
        (51, DummyStatusEnum.FAILED),
        (46, DummyStatusEnum.REJECTED),
        (50, DummyStatusEnum.REJECTED),
        (49, DummyStatusEnum.SUBMITTED),
    ]

    status_sort_clause = sort_clause("status", DummySortTable.sortable_fields(), False)
    query = select(DummySortTable).order_by(status_sort_clause, "id")
    result = await synth_session.scalars(query)
    assert [(d.id, d.status) for d in result.all()] == [
        (49, DummyStatusEnum.SUBMITTED),
        (46, DummyStatusEnum.REJECTED),
        (50, DummyStatusEnum.REJECTED),
        (45, DummyStatusEnum.FAILED),
        (51, DummyStatusEnum.FAILED),
        (48, DummyStatusEnum.CREATED),
        (44, DummyStatusEnum.COMPLETED),
        (47, DummyStatusEnum.COMPLETED),
    ]


async def test_handle_fk_error():
    """
    Provide a test for the ``handle_fk_error()`` fastapi error handler.
    """
    fk_error = asyncpg.exceptions.ForeignKeyViolationError('''DETAIL:  Key (id)=(13) is still referenced from table "blah"''')
    response = handle_fk_error(None, fk_error)
    response_data = json.loads(response.body.decode())
    assert response_data["detail"]["message"] == "Delete failed due to foreign-key constraint"
    assert response_data["detail"]["table"] == "blah"
    assert response_data["detail"]["pk_id"] == "13"
