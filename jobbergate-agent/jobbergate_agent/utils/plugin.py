"""
Provide to the agent the ability to load custom plugins that are installed on the same environment.
"""

from typing import Any, Dict

from buzz import handle_errors
from pluggy import PluginManager

from jobbergate_agent.utils.logging import logger, logger_wraps


@logger_wraps()
def load_plugins(plugin_name: str) -> Dict[str, Any]:
    """
    Discover and load plugins available to the agent, allowing for third party ones to be included.

    Notice the ones shipped with the agent are also declared on the ``pyproject.toml`` file
    as plugins, even though they could be easily loaded directly from source. This aims
    to support tests and to demonstrate how to use the plugin system.
    """
    project_name = "jobbergate_agent"
    plugin_group = f"{project_name}.{plugin_name}"
    pm = PluginManager(project_name=project_name)
    pm.load_setuptools_entrypoints(group=plugin_group)

    with handle_errors(f"Failed to load plugins from {plugin_group}", raise_exc_class=RuntimeError):
        result = {name: plugin for name, plugin in pm.list_name_plugin()}

    logger.info("Discovered the following plugins for {}: {}", plugin_name, ", ".join(result.keys()))
    return result
