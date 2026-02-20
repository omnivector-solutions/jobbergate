"""
Utility functions for implementing retry logic with exponential backoff.
"""

import asyncio
from typing import Awaitable, Callable, Optional, TypeVar

from loguru import logger

T = TypeVar("T")


async def async_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    on_error: Optional[Callable[[Exception, int], None]] = None,
    **kwargs,
) -> Optional[T]:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay between retries
        on_error: Optional callback function(exception, attempt_num) for error handling
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func if successful, None if all retries exhausted

    Example:
        result = await async_retry(
            my_async_function,
            arg1, arg2,
            max_attempts=3,
            initial_delay=1.0,
            on_error=lambda exc, attempt: logger.warning(f"Attempt {attempt} failed: {exc}"),
            kwarg1=value1
        )
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if on_error:
                on_error(exc, attempt)
            else:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {exc}")

            if attempt < max_attempts:
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    f"All {max_attempts} retry attempts exhausted for {func.__name__}: {last_exception}"
                )

    return None


def sync_retry(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    on_error: Optional[Callable[[Exception, int], None]] = None,
    **kwargs,
) -> Optional[T]:
    """
    Retry a sync function with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay between retries
        on_error: Optional callback function(exception, attempt_num) for error handling
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func if successful, None if all retries exhausted
    """
    import time

    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if on_error:
                on_error(exc, attempt)
            else:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {exc}")

            if attempt < max_attempts:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    f"All {max_attempts} retry attempts exhausted for {func.__name__}: {last_exception}"
                )

    return None
