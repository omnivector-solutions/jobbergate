"""
Provide initializers for logging.
"""

import sys

import sentry_sdk
from loguru import logger

from jobbergate_cli.config import settings


def init_logs(verbose=False):
    """
    Initialize logging.

    If JOBBERGATE_LOG_PATH is set in the config, add a rotatating file log handler.
    Logs will be retained for 1 week.

    If verbose is supplied, add a stdout handler at the DEBUG level.
    """
    # Remove default stderr handler at level INFO
    logger.remove()

    if verbose:
        logger.add(sys.stdout, level="DEBUG")

    if settings.JOBBERGATE_LOG_PATH is not None:
        logger.add(settings.JOBBERGATE_LOG_PATH, rotation="00:00", retention="1 week", level="DEBUG")
    logger.debug("Logging initialized")


def init_sentry():
    """
    Initialize Sentry if the ``SENTRY_DSN`` environment variable is present.
    """
    if settings.SENTRY_DSN:
        logger.debug("Initializing sentry")
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACE_RATE,
            environment=settings.SENTRY_ENV,
        )
