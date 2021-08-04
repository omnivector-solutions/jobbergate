"""
All the routers of the resources
"""
from importlib import import_module
from loguru import logger

app_routers = [
    "jobbergateapi2.apps.users.routers",
    "jobbergateapi2.apps.auth.routers",
    "jobbergateapi2.apps.applications.routers",
    "jobbergateapi2.apps.permissions.routers",
    "jobbergateapi2.apps.job_scripts.routers",
    "jobbergateapi2.apps.job_submissions.routers",
]


def load_routers(app):
    """
    Load all routers
    """
    logger.debug("Loading routes")
    for path in app_routers:
        module = import_module(path)
        logger.debug(f"Loading router for {module=}")

        function = getattr(module, "include_router")
        function(app)

        logger.info(f"Initialized router to {path}")
