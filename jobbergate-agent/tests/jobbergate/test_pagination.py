"""
Test the pagination utilities in the jobbergate_agent module.
"""

import json
import math

import pydantic
import pytest
import respx
from httpx import Response
from polyfactory.factories.pydantic_factory import ModelFactory

from jobbergate_agent.jobbergate.pagination import fetch_page, fetch_paginated_result
from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, ListResponseEnvelope, PendingJobSubmission


class PendingJobSubmissionFactory(ModelFactory[PendingJobSubmission]):
    """Factory for generating test data based on PendingJobSubmission objects."""

    __model__ = PendingJobSubmission


class ActiveJobSubmissionFactory(ModelFactory[ActiveJobSubmission]):
    """Factory for generating test data based on ActiveJobSubmission objects."""

    __model__ = ActiveJobSubmission


def single_paged_items_wrapper(items: list[pydantic.BaseModel]) -> ListResponseEnvelope:
    """
    Wrap a list of items into a single-page ListResponseEnvelope.

    Args:
        items: A list of pydantic models to include in the response.

    Returns:
        A ListResponseEnvelope containing the items.
    """
    total = len(items)
    return ListResponseEnvelope(items=items, total=total, page=1, size=total, pages=0 if total == 0 else 1)


def multi_paged_items_wrapper(items: list[pydantic.BaseModel], page_size: int) -> list[ListResponseEnvelope]:
    """
    Wrap a list of items into multiple pages of ListResponseEnvelope.

    Args:
        items: A list of pydantic models to include in the response.
        page_size: The number of items per page.

    Returns:
        A list of ListResponseEnvelope objects representing paginated data.
    """
    total = len(items)
    pages = 0 if total == 0 else math.ceil(total / page_size)
    return [
        ListResponseEnvelope(
            items=items[i : i + page_size], total=total, page=i // page_size + 1, size=page_size, pages=pages
        )
        for i in range(0, total, page_size)
    ]


@pytest.mark.parametrize(
    "base_model, factory",
    [
        (PendingJobSubmission, PendingJobSubmissionFactory),
        (ActiveJobSubmission, ActiveJobSubmissionFactory),
    ],
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
class TestFetchPage:
    """
    Test the `fetch_page` function for handling single-page API responses.
    """

    async def test_fetch_page__success(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_page` successfully retrieves a single page of data.
        """
        TARGET_PAGE = 1
        ITEMS_PER_PAGE = 10

        mock_data = factory.batch(ITEMS_PER_PAGE)
        mock_response = single_paged_items_wrapper(items=mock_data)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE):
            route = respx.get("mock-url", params=dict(page=TARGET_PAGE, size=ITEMS_PER_PAGE)).mock(
                return_value=Response(200, content=mock_response.model_dump_json())
            )
            results = await fetch_page("mock-url", base_model, page=TARGET_PAGE)

        assert route.call_count == 1
        assert mock_response == results
        assert all(isinstance(item, base_model) for item in results.items)

    async def test_fetch_page__empty_response(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_page` handles an empty response gracefully.
        """
        ITEMS_PER_PAGE = 10

        mock_data = []
        mock_response = single_paged_items_wrapper(items=mock_data)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE):
            route = respx.get("mock-url", params=dict(size=ITEMS_PER_PAGE)).mock(
                return_value=Response(200, content=mock_response.model_dump_json())
            )

            results = await fetch_page("mock-url", base_model, page=1)

        assert route.call_count == 1
        assert results.pages == 0
        assert results == mock_response

    async def test_fetch_page__request_error(self, base_model, factory):
        """
        Test that `fetch_page` raises an exception when the API returns an error.
        """
        with respx.mock, pytest.raises(Exception, match="Internal Server Error"):
            route = respx.get("mock-url").mock(return_value=Response(500, json={"detail": "Internal Server Error"}))
            await fetch_page("mock-url", base_model, page=1)

        assert route.call_count == 1

    async def test_fetch_page__json_error(self, base_model, factory):
        """
        Test that `fetch_page` raises an exception when the API response contains invalid JSON.
        """
        with respx.mock, pytest.raises(json.decoder.JSONDecodeError):
            route = respx.get("mock-url").mock(return_value=Response(200, content="invalid json"))
            await fetch_page("mock-url", base_model, page=1)

        assert route.call_count == 1

    async def test_fetch_page__validation_error(self, base_model, factory):
        """
        Test that `fetch_page` raises a validation error when the API response is invalid.
        """
        with respx.mock, pytest.raises(pydantic.ValidationError):
            route = respx.get("mock-url").mock(return_value=Response(200, json={"detail": "Internal Server Error"}))
            await fetch_page("mock-url", base_model, page=1)

        assert route.call_count == 1


@pytest.mark.parametrize(
    "base_model, factory",
    [
        (PendingJobSubmission, PendingJobSubmissionFactory),
        (ActiveJobSubmission, ActiveJobSubmissionFactory),
    ],
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
class TestFetchPaginatedResult:
    """
    Test the `fetch_paginated_result` function for handling multi-page API responses.
    """

    async def test_fetch_paginated_result__success(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_paginated_result` successfully retrieves a single page of data.
        """
        TARGET_PAGE = 1
        ITEMS_PER_PAGE = 10

        mock_data = factory.batch(ITEMS_PER_PAGE)
        mock_response = single_paged_items_wrapper(items=mock_data)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE):
            route = respx.get("mock-url", params=dict(page=TARGET_PAGE, size=ITEMS_PER_PAGE)).mock(
                return_value=Response(200, content=mock_response.model_dump_json())
            )

            results = await fetch_paginated_result("mock-url", base_model)

        assert route.call_count == 1
        assert results == mock_response.items

    async def test_fetch_paginated_result__multiple_pages(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_paginated_result` retrieves data across multiple pages.
        """
        ITEMS_PER_PAGE = 5
        MAX_PAGES_PER_CYCLE = 5

        mock_data = factory.batch(ITEMS_PER_PAGE * MAX_PAGES_PER_CYCLE)
        mock_response = multi_paged_items_wrapper(items=mock_data, page_size=ITEMS_PER_PAGE)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE, MAX_PAGES_PER_CYCLE=MAX_PAGES_PER_CYCLE):
            route = respx.get("mock-url")
            route.side_effect = (Response(200, content=page.model_dump_json()) for page in mock_response)

            results = await fetch_paginated_result("mock-url", base_model)

        assert route.call_count == MAX_PAGES_PER_CYCLE
        assert results == [item for page in mock_response for item in page.items]

    async def test_fetch_paginated_result__multiple_pages_prevents_overflow(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_paginated_result` does not overflow when the total data exceeds the maximum pages.
        """
        ITEMS_PER_PAGE = 5
        MAX_PAGES_PER_CYCLE = 5

        mock_data = factory.batch(ITEMS_PER_PAGE * MAX_PAGES_PER_CYCLE + 1)  # extra data to test overflow
        mock_response = multi_paged_items_wrapper(items=mock_data, page_size=ITEMS_PER_PAGE)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE, MAX_PAGES_PER_CYCLE=MAX_PAGES_PER_CYCLE):
            route = respx.get("mock-url")
            route.side_effect = (Response(200, content=page.model_dump_json()) for page in mock_response)

            results = await fetch_paginated_result("mock-url", base_model)

        assert route.call_count == MAX_PAGES_PER_CYCLE
        assert len(results) == len(mock_data) - 1  # exclude the last item
        assert results == [item for page in mock_response[:MAX_PAGES_PER_CYCLE] for item in page.items]

    async def test_fetch_paginated_result__empty_response(self, base_model, factory, tweak_settings):
        """
        Test that `fetch_paginated_result` handles an empty response gracefully.
        """
        ITEMS_PER_PAGE = 10

        mock_data = []
        mock_response = single_paged_items_wrapper(items=mock_data)

        with respx.mock, tweak_settings(ITEMS_PER_PAGE=ITEMS_PER_PAGE):
            route = respx.get("mock-url", params=dict(size=ITEMS_PER_PAGE)).mock(
                return_value=Response(200, content=mock_response.model_dump_json())
            )

            results = await fetch_paginated_result("mock-url", base_model)

        assert route.call_count == 1
        assert results == mock_response.items
