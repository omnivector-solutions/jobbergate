from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.utils.exception import JobbergateApiError
from jobbergate_agent.utils.logging import log_error


async def report_health_status(interval: int) -> None:
    """Ping the API to report the agent's status."""
    logger.debug("Reporting status to the API")
    with JobbergateApiError.handle_errors("Failed to report agent status", do_except=log_error):
        response = await jobbergate_api_client.put("jobbergate/clusters/status", params={"interval": interval})
        response.raise_for_status()
