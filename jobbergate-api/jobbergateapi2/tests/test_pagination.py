"""
Test the pagination.
"""
import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.pagination import Pagination, package_response
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects


def test_init_fails_on_invalid_parameters():
    """
    Tests that the parameters are valid or an exception will be raised.
    """
    with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
        Pagination(page=-1, per_page=1)

    with pytest.raises(ValidationError, match="ensure this value is greater than 0"):
        Pagination(page=1, per_page=0)


def test_string_conversion():
    """
    Test the pagination as string.
    """
    pagination = Pagination(page=13, per_page=21)

    assert str(pagination) == "page=13 per_page=21"


def test_dict():
    """
    Test the dict() method on a pagination instance.
    """
    pagination = Pagination(page=13, per_page=21)
    assert pagination.dict() == dict(page=13, per_page=21)

    pagination = Pagination(page=None, per_page=999)
    assert pagination.dict() == dict()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_package_response__without_pagination():
    """
    Test the package_response method without pagination.
    """
    application_data = dict(
        application_name="test_name",
        application_file="the\nfile",
        application_config="the configuration is here",
    )
    applications = [
        Application(id=i, application_owner_id=f"owner{i}", **application_data) for i in range(1, 6)
    ]
    await insert_objects(applications, applications_table)

    query = applications_table.select()
    pagination = Pagination()
    response = await package_response(Application, query, pagination)

    results = response.results
    assert len(results) == 5
    for i in range(5):
        assert isinstance(results[i], Application)
        assert results[i].id == i + 1

    metadata = response.metadata
    assert metadata
    assert metadata.total == 5
    assert metadata.page is None
    assert metadata.per_page is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page,per_page,total", [(0, 1, 1), (6, 2, 13), (2, 3, 10), (7, 2, 13)],
)
@database.transaction(force_rollback=True)
async def test_package_response__with_pagination(page, per_page, total):
    """
    Test the package_response method with pagination.

    Parameters test pagination at upper bound and lower bound of total
    """
    application_data = dict(
        application_name="test_name",
        application_file="the\nfile",
        application_config="the configuration is here",
    )
    applications = [
        Application(id=i, application_owner_id=f"owner{i}", **application_data) for i in range(1, total + 1)
    ]
    await insert_objects(applications, applications_table)

    query = applications_table.select()
    pagination = Pagination(page=page, per_page=per_page)
    response = await package_response(Application, query, pagination)

    results = response.results
    # Clamps the expected count at upper bound
    expected_count = max(0, min(total - page * per_page, per_page))
    assert len(results) == expected_count
    for i in range(expected_count):
        assert isinstance(results[i], Application)
        assert results[i].id == i + (page * per_page) + 1

    metadata = response.metadata
    assert metadata
    assert metadata.total == total
    assert metadata.page == page
    assert metadata.per_page == per_page
