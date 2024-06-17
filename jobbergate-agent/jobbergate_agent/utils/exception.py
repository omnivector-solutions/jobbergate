"""Core module for exception related operations"""

import contextlib
from asyncio import iscoroutinefunction
from typing import Any, AsyncIterator, Callable, Coroutine, Iterable, Mapping, Optional, Tuple, Type, Union

from buzz import Buzz, get_traceback, reformat_exception
from buzz.tools import DoExceptParams, noop


class ClusterAgentError(Buzz):
    """Raise exception when execution command returns an error"""


class ProcessExecutionError(ClusterAgentError):
    """Raise exception when execution command returns an error"""


class AuthTokenError(ClusterAgentError):
    """Raise exception when there are connection issues with the backend"""


class SbatchError(ClusterAgentError):
    """Raise exception when sbatch raises any error"""


class JobbergateApiError(ClusterAgentError):
    """Raise exception when communication with Jobbergate API fails"""


class JobSubmissionError(ClusterAgentError):
    """Raise exception when a job cannot be submitted raises any error"""


class SlurmParameterParserError(ClusterAgentError):
    """Raise exception when Slurm mapper or SBATCH parser face any error"""


@contextlib.asynccontextmanager
async def handle_errors_async(
    message: str,
    raise_exc_class: Union[Type[Exception], None] = Exception,
    raise_args: Optional[Iterable[Any]] = None,
    raise_kwargs: Optional[Mapping[str, Any]] = None,
    handle_exc_class: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    do_finally: Callable[[], None] | Callable[[], Coroutine[Any, Any, None]] = noop,
    do_except: Callable[[DoExceptParams], None] | Callable[[DoExceptParams], Coroutine[Any, Any, None]] = noop,
    do_else: Callable[[], None] | Callable[[], Coroutine[Any, Any, None]] = noop,
) -> AsyncIterator[None]:
    """
    Async context manager that will intercept exceptions and repackage them with a message attached.

    Example:

    .. code-block:: python

       with handle_errors("It didn't work"):
           some_code_that_might_raise_an_exception()

    :param: message:           The message to attach to the raised exception.
    :param: raise_exc_class:   The exception type to raise with the constructed message
                               if an exception is caught in the managed context.

                               Defaults to Exception.

                               If ``None`` is passed, no new exception will be raised and only the
                               ``do_except``, ``do_else``, and ``do_finally``
                               functions will be called.
    :param: raise_args:        Additional positional args (after the constructed message) that will
                               passed when raising an instance of the ``raise_exc_class``.
    :param: raise_kwargs:      Keyword args that will be passed when raising an instance of the
                               ``raise_exc_class``.
    :param: handle_exc_class:  Limits the class of exceptions that will be intercepted
                               Any other exception types will not be caught and re-packaged.
                               Defaults to Exception (will handle all exceptions). May also be
                               provided as a tuple of multiple exception types to handle.
    :param: do_finally:        A function that should always be called at the end of the block.
                               Should take no parameters.
    :param: do_except:         A function that should be called only if there was an exception.
                               Must accept one parameter that is an instance of the
                               ``DoExceptParams`` dataclass. Note that the ``do_except``
                               method is passed the *original exception*.
    :param: do_else:           A function that should be called only if there were no
                               exceptions encountered.
    """
    try:
        yield
    except handle_exc_class as err:
        try:
            final_message = reformat_exception(message, err)
        except Exception as msg_err:
            raise RuntimeError(f"Failed while formatting message: {repr(msg_err)}")

        trace = get_traceback()

        if iscoroutinefunction(do_except):
            await do_except(DoExceptParams(err, final_message, trace))
        else:
            do_except(DoExceptParams(err, final_message, trace))

        if raise_exc_class is not None:
            args = raise_args or []
            kwargs = raise_kwargs or {}
            raise raise_exc_class(final_message, *args, **kwargs).with_traceback(trace)
    else:
        if iscoroutinefunction(do_else):
            await do_else()
        else:
            do_else()
    finally:
        if iscoroutinefunction(do_finally):
            await do_finally()
        else:
            do_finally()
