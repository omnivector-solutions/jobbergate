"""
Test the pagination.
"""

import json

import pytest
from pydantic import ValidationError

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.pagination import Pagination, Response, package_response
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
                application_owner_email=f"owner{i}@org.com",
                application_name=f"app{i}",
            )
            for i in range(1, 6)
        ],
    )

    query = applications_table.select()
    pagination = Pagination()
    raw_response = await package_response(ApplicationResponse, query, pagination)
    response = Response[ApplicationResponse].parse_obj(json.loads(raw_response.body))

    results = response.results
    assert len(results) == 5
    for (i, result) in enumerate(results):
        assert isinstance(result, ApplicationResponse)
        assert result.application_name == f"app{i + 1}"

    assert response.pagination.total == 5
    assert response.pagination.start is None
    assert response.pagination.limit is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start,limit,total",
    [(0, 1, 1), (6, 2, 13), (2, 3, 10), (7, 2, 13)],
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
                application_name=f"app{i}",
            )
            for i in range(1, total + 1)
        ],
    )

    query = applications_table.select()
    pagination = Pagination(start=start, limit=limit)
    raw_response = await package_response(ApplicationResponse, query, pagination)
    response = Response[ApplicationResponse].parse_obj(json.loads(raw_response.body))

    results = response.results
    # Clamps the expected count at upper bound
    expected_count = max(0, min(total - start * limit, limit))
    assert len(results) == expected_count
    for (i, result) in enumerate(results):
        assert isinstance(result, ApplicationResponse)
        assert result.application_name == f"app{i + (start * limit) + 1}"

    assert response.pagination
    assert response.pagination.total == total
    assert response.pagination.start == start
    assert response.pagination.limit == limit
