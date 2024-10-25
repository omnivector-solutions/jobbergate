"""
Provide functions to configure logging.
"""

import dataclasses
import inspect
import logging
import sys

from loguru import logger

from jobbergate_api.config import settings


class InterceptHandler(logging.Handler):
    """
    Specialized handler to intercept log lines sent to standard logging by 3rd party tools.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        Handle emission of the log record.
        """
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


@dataclasses.dataclass
class RouteFilterParams:
    """
    Defines the params for a UvicornRouteFilter.
    """

    route: str
    verb: str = "GET"


class UvicornRouteFilter(logging.Filter):
    """
    Define a logging filter for uvicorn routes.
    """

    def __init__(self, rfp: RouteFilterParams):
        """
        Initialize with route filter params.
        """
        self.rfp = rfp

    def filter(self, record):
        """
        Filter messages matching the verb and route.
        """
        return f"{self.rfp.verb} {self.rfp.route}" not in record.getMessage()


def init_logging(supress_routes: list[RouteFilterParams] | None = None):
    """
    Initialize logging by setting log level for normal logger and for the SQL logging.
    """
    if supress_routes is None:
        supress_routes = []

    engine_logger = logging.getLogger("sqlalchemy.engine")
    engine_logger.setLevel(settings.SQL_LOG_LEVEL.value)
    engine_logger.handlers = [InterceptHandler()]

    pool_logger = logging.getLogger("sqlalchemy.pool")
    pool_logger.setLevel(settings.SQL_LOG_LEVEL.value)
    pool_logger.handlers = [InterceptHandler()]

    uvicorn_logger = logging.getLogger("uvicorn.access")
    for rfp in supress_routes:
        uvicorn_logger.addFilter(UvicornRouteFilter(rfp))

    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL)
    logger.info(f"Logging configured 📝 Level: {settings.LOG_LEVEL}, SQL Level: {settings.SQL_LOG_LEVEL}")
