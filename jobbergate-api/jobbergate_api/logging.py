"""
Provide functions to configure logging.
"""

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


def init_logging():
    """
    Initialize logging by setting log level for normal logger and for the SQL logging.
    """
    engine_logger = logging.getLogger("sqlalchemy.engine")
    engine_logger.setLevel(settings.SQL_LOG_LEVEL.value)
    engine_logger.handlers = [InterceptHandler()]

    pool_logger = logging.getLogger("sqlalchemy.pool")
    pool_logger.setLevel(settings.SQL_LOG_LEVEL.value)
    pool_logger.handlers = [InterceptHandler()]

    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL)
    logger.info(f"Logging configured 📝 Level: {settings.LOG_LEVEL}, SQL Level: {settings.SQL_LOG_LEVEL}")
