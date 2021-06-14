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
    "jobbergateapi2.apps.application_permissions.routers",
    "jobbergateapi2.apps.job_scripts.routers",
    "jobbergateapi2.apps.job_submissions.routers",
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
