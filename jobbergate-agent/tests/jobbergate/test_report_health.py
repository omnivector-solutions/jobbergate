import httpx
import pytest
import respx

from jobbergate_agent.jobbergate.report_health import report_health_status
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_report_health_status__success():
    interval = 60
    async with respx.mock:
        status_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/clusters/status")
        status_route.mock(return_value=httpx.Response(status_code=202))

        await report_health_status(interval)

    assert status_route.call_count == 1
    assert dict(status_route.calls.last.request.url.params) == {"interval": str(interval)}


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_report_health_status__failure():
    interval = 60
    async with respx.mock:
        status_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/clusters/status")
        status_route.mock(return_value=httpx.Response(status_code=500))

        with pytest.raises(JobbergateApiError):
            await report_health_status(interval)

    assert status_route.call_count == 1
    assert dict(status_route.calls.last.request.url.params) == {"interval": str(interval)}
