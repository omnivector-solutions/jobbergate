"""
Provide unit tests for the main app.
"""
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """
    Test the health check route.

    This test ensures the API has a health check path configured properly, so
    the production and staging environments can configure the load balancing
    """
    response = await client.get("/jobbergate/health")

    assert response.status_code == status.HTTP_204_NO_CONTENT
