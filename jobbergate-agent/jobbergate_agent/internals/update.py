import subprocess
import sys

from loguru import logger
from pkg_resources import get_distribution

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.utils.scheduler import schedule_tasks, scheduler


package_name = "jobbergate_agent"


async def _fetch_upstream_version_info() -> str:
    logger.debug("Fetching the upstream version info from jobbergate API")
    response = await jobbergate_api_client.get("/jobbergate/openapi.json")
    response.raise_for_status()

    data = response.json()
    upstream_version: str = data["info"]["version"]
    return upstream_version


def _compare_versions(current_version: str, upstream_version: str) -> bool:
    """Compare the current version with the upstream version.

    In case the current version is the same as the upstream version, return False.
    As well as, in case the major versions are the same, return False, as we don't want
    to update across major versions. Otherwise, return True.

    This behaviour allows the agent to update and rollback across all minor and patch versions.
    """
    if current_version == upstream_version:
        return False
    current_major, _, _ = map(int, current_version.split("."))
    upstream_major, _, _ = map(int, upstream_version.split("."))
    if current_major != upstream_major:
        return False
    return True


def _update_package(version: str) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", f"{package_name}=={version}"])


async def self_update_agent():
    """Fetch the upstream version and update the agent if necessary.

    In case the agent is updated, the scheduler is shutdown and restarted with the new version.
    """
    current_version = get_distribution(package_name).version
    upstream_version = await _fetch_upstream_version_info()
    logger.debug(
        f"Jobbergate Agent version info: current_version={current_version}, upstream_version={upstream_version}"
    )

    if _compare_versions(current_version, upstream_version):
        logger.warning("The Jobbergate Agent is outdated in relation of the upstream version, an update is required.")

        logger.debug("Shutting down the scheduler...")
        scheduler.shutdown(wait=False)

        logger.debug(f"Updating {package_name} from version {current_version} to {upstream_version}...")
        _update_package(upstream_version)
        logger.debug("Update completed successfully.")

        logger.debug(f"Loading plugins from version {upstream_version}...")
        schedule_tasks(scheduler)
        logger.debug("Plugins loaded successfully.")
    else:
        logger.debug("No update is required or update crosses a major version divide.")
