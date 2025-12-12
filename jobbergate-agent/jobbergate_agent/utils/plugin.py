"""
Provide to the agent the ability to load custom plugins that are installed on the same environment.
"""

from typing import Any, Dict, Sequence

from buzz import handle_errors
from pluggy import HookimplMarker, HookspecMarker, PluginManager

from jobbergate_agent.utils.logging import logger, logger_wraps


PROJECT_NAME = "jobbergate_agent"

hookspec = HookspecMarker(PROJECT_NAME)
hookimpl = HookimplMarker(PROJECT_NAME)


def get_plugin_manager(
    plugin_name: str, hookspec_class: None | Any = None, register: None | Sequence[Any] = None
) -> PluginManager:
    """
    Get a PluginManager instance for the agent.
    """
    plugin_group = f"{PROJECT_NAME}.{plugin_name}"
    plugin_manager = PluginManager(project_name="jobbergate_agent")
    if hookspec_class is not None:
        plugin_manager.add_hookspecs(hookspec_class)

    plugin_sequence = register or []
    for i in plugin_sequence:
        plugin_manager.register(i)

    plugin_manager.load_setuptools_entrypoints(group=plugin_group)

    return plugin_manager


@logger_wraps()
def load_plugins(plugin_name: str) -> Dict[str, Any]:
    """
    Discover and load plugins available to the agent, allowing for third party ones to be included.

    Notice the ones shipped with the agent are also declared on the ``pyproject.toml`` file
    as plugins, even though they could be easily loaded directly from source. This aims
    to support tests and to demonstrate how to use the plugin system.
    """
    plugin_manager = get_plugin_manager(plugin_name)

    with handle_errors(f"Failed to load plugins from {plugin_name}", raise_exc_class=RuntimeError):
        result = dict(plugin_manager.list_name_plugin())

    logger.info("Discovered the following plugins for {}: {}", plugin_name, ", ".join(result.keys()))
    return result
