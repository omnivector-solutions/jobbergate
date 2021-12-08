"""
Test the pagination.
"""
from jobbergate_api.pagination import Pagination


def test_string_conversion():
    """
    Test the pagination as string.
    """
    pagination = Pagination()

    assert str(pagination) == f"limit: {pagination.limit}, skip: {pagination.skip}"


def test_pagination_with_default_values():
    """
    Test the pagination default values.
    """
    pagination = Pagination()

    assert pagination.limit == 10
    assert pagination.skip == 0


def test_pagination_with_custom_values():
    """
    Test the pagination with custom values.
    """
    pagination = Pagination(limit=100, skip=1)

    assert pagination.limit == 100
    assert pagination.skip == 1
