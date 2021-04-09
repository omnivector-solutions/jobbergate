"""
All the routers of the resources
"""
import logging
from importlib import import_module

logger = logging.getLogger(__name__)

app_routers = [
    "jobbergateapi2.apps.users.routers",
    "jobbergateapi2.apps.auth.routers",
    "jobbergateapi2.apps.applications.routers",
]


def load_routers(app):
    """
    Load all routers
    """
    for path in app_routers:
        module = import_module(path)

        function = getattr(module, "include_router")
        function(app)

        logger.info("Initialized router to %s", path)
