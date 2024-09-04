"""Core module for logging operations"""

import functools
from traceback import format_tb

from buzz import DoExceptParams
from loguru import logger


def log_error(params: DoExceptParams):
    """
    Provide a utility function to log a Buzz-based exception and the stack-trace of
    the error's context.

    Args:
        params: A DoExceptParams instance containing the original exception, a
            message describing it, and the stack trace of the error.
    """
    logger.error(
        "\n".join(
            [
                params.final_message,
                "--------",
                "Traceback:",
                "".join(format_tb(params.trace)),
            ]
        )
    )


def logger_wraps(*, entry: bool = True, exit: bool = True, level: str = "DEBUG"):
    """
    Decorator to wrap a function with logging statements.

    Reference:
        https://loguru.readthedocs.io/en/stable/resources/recipes.html
    """

    def wrapper(func):
        name = func.__name__

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            logger_ = logger.opt(depth=1)
            if entry:
                logger_.log(level, "Entering '{}' (args={}, kwargs={})", name, args, kwargs)
            result = func(*args, **kwargs)
            if exit:
                logger_.log(level, "Exiting '{}' (result={})", name, result)
            return result

        return wrapped

    return wrapper
