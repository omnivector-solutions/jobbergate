"""
Helper functions for paginating through the Jobbergate API.
"""

from typing import Type, TypeVar

import pydantic
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.jobbergate.schemas import ListResponseEnvelope
from jobbergate_agent.settings import SETTINGS

T = TypeVar("T", bound=pydantic.BaseModel)


async def fetch_page(url: str, base_model: Type[T], page: int = 1) -> ListResponseEnvelope[T]:
    """
    Retrieve a page of job submissions.
    """
    response_model = ListResponseEnvelope[base_model]  # type: ignore
    response = await jobbergate_api_client.get(url, params=dict(page=page, size=SETTINGS.ITEMS_PER_PAGE))
    response.raise_for_status()
    result = response_model.model_validate(response.json())
    logger.debug("Retrieved page {} out of {} for {}", result.page, result.pages, url)
    return result


async def fetch_paginated_result(url: str, base_model: Type[T]) -> list[T]:
    """
    Retrieve a list of job submissions.
    """
    results = []
    for page in range(1, SETTINGS.MAX_PAGES_PER_CYCLE + 1):
        page_entries = await fetch_page(url, base_model, page)
        results.extend(page_entries.items)
        if page_entries.page >= page_entries.pages:
            break

    return results
