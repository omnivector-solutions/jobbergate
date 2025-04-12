from typing import TypeVar

import pytest
from pydantic import BaseModel

from jobbergate_core.sdk.schemas import ListResponseEnvelope


@pytest.fixture(scope="session")
def wrap_items_on_paged_response():
    PagedItem = TypeVar("PagedItem", bound=BaseModel)

    def helper(items: list[PagedItem]) -> ListResponseEnvelope[PagedItem]:
        """
        Wrap a list of items into a single-page ListResponseEnvelope.
        Args:
            items: A list of pydantic models to include in the response.
        Returns:
            A ListResponseEnvelope containing the items.
        """
        total = len(items)
        pages = 1 if total else 0
        return ListResponseEnvelope(items=items, total=total, page=1, size=total, pages=pages)

    return helper
