"""
Test the pagination.
"""
import pytest
from pydantic import ValidationError

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.pagination import Pagination, package_response
from jobbergate_api.storage import database


def test_init_fails_on_invalid_parameters():
    """
    Tests that the parameters are valid or an exception will be raised.
    """
    with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
        Pagination(start=-1, limit=1)

    with pytest.raises(ValidationError, match="ensure this value is greater than 0"):
        Pagination(start=1, limit=0)


def test_string_conversion():
    """
    Test the pagination as string.
    """
    pagination = Pagination(start=13, limit=21)

    assert str(pagination) == "start=13 limit=21"


def test_dict():
    """
    Test the dict() method on a pagination instance.
    """
    pagination = Pagination(start=13, limit=21)
    assert pagination.dict() == dict(start=13, limit=21)

    pagination = Pagination(start=None, limit=999)
    assert pagination.dict() == dict()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_package_response__without_pagination():
    """
    Test the package_response method without pagination.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=[
            dict(
                id=i,
                application_owner_email=f"owner{i}@org.com",
                application_name="test_name",
                application_file="the\nfile",
                application_config="the configuration is here",
            )
            for i in range(1, 6)
        ],
    )

    query = applications_table.select()
    pagination = Pagination()
    response = await package_response(ApplicationResponse, query, pagination)

    results = response.results
    assert len(results) == 5
    for i in range(5):
        assert isinstance(results[i], ApplicationResponse)
        assert results[i].id == i + 1

    pagination = response.pagination
    assert pagination
    assert pagination.total == 5
    assert pagination.start is None
    assert pagination.limit is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start,limit,total", [(0, 1, 1), (6, 2, 13), (2, 3, 10), (7, 2, 13)],
)
@database.transaction(force_rollback=True)
async def test_package_response__with_pagination(start, limit, total):
    """
    Test the package_response method with pagination.

    Parameters test pagination at upper bound and lower bound of total
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=[
            dict(
                id=i,
                application_owner_email=f"owner{i}@org.com",
                application_name="test_name",
                application_file="the\nfile",
                application_config="the configuration is here",
            )
            for i in range(1, total + 1)
        ],
    )

    query = applications_table.select()
    pagination = Pagination(start=start, limit=limit)
    response = await package_response(ApplicationResponse, query, pagination)

    results = response.results
    # Clamps the expected count at upper bound
    expected_count = max(0, min(total - start * limit, limit))
    assert len(results) == expected_count
    for i in range(expected_count):
        assert isinstance(results[i], ApplicationResponse)
        assert results[i].id == i + (start * limit) + 1

    pagination = response.pagination
    assert pagination
    assert pagination.total == total
    assert pagination.start == start
    assert pagination.limit == limit
