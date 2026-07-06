"""
Provides a data object for context passed from the main entry point.

Also provides the *active context* mechanism: a ``ContextVar`` holding the current
``JobbergateContext`` so CLI commands can be called directly as regular functions
(e.g. from a ``jobbergate.py`` application script running in-process).
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import cached_property
from typing import Iterator, cast

import click
import typer
from buzz import check_expressions
from httpx import Client

from jobbergate_cli.auth import show_login_message, track_login_progress
from jobbergate_cli.config import settings
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ContextProtocol
from jobbergate_core.auth.handler import JobbergateAuthHandler
from jobbergate_core.sdk import Apps


@dataclass
class JobbergateContext(ContextProtocol):
    """
    A data object describing context passed from the main entry point.
    """

    raw_output: bool = False
    full_output: bool = False

    @cached_property
    def client(self) -> Client:
        """
        Client for making requests to the Jobbergate API.
        """
        return Client(
            base_url=settings.BASE_API_URL,
            auth=self.authentication_handler,
            timeout=settings.JOBBERGATE_REQUESTS_TIMEOUT,
        )

    @cached_property
    def authentication_handler(self) -> JobbergateAuthHandler:
        """
        The authentication handler for the context.

        This is a cached property to ensure that the handler is only created when needed,
        so commands that require no authentication face no configuration errors.
        """
        with check_expressions(
            "The following settings are required to enable authenticated requests:",
            raise_exc_class=Abort,
            raise_kwargs={"support": True, "subject": "Configuration error"},
        ) as check:
            check(settings.OIDC_DOMAIN, "OIDC_DOMAIN")
            check(settings.OIDC_CLIENT_ID, "OIDC_CLIENT_ID")

        protocol = "https" if settings.OIDC_USE_HTTPS else "http"
        return JobbergateAuthHandler(
            cache_directory=settings.JOBBERGATE_USER_TOKEN_DIR,
            login_domain=f"{protocol}://{settings.OIDC_DOMAIN}",
            login_client_id=settings.OIDC_CLIENT_ID,
            login_client_secret=settings.OIDC_CLIENT_SECRET,
            login_url_handler=show_login_message,
            login_sequence_handler=track_login_progress,
        )

    @cached_property
    def sdk(self) -> Apps:
        """
        SDK for accessing Jobbergate API.
        """
        return Apps(client=self.client)


_active_context: ContextVar[ContextProtocol | None] = ContextVar("jobbergate_active_context", default=None)
"""
The active Jobbergate context for the current execution context.

It is set by the CLI entry point, making the context available to commands called directly as
regular functions (e.g. from a ``jobbergate.py`` application script running in-process).

Notice ``ContextVar`` values do not propagate to threads started with ``threading.Thread``,
so each new thread needs its own active context (or an explicit context passed as an override).
"""


def set_active_context(context: ContextProtocol) -> Token[ContextProtocol | None]:
    """
    Set the active Jobbergate context and return a token that can restore the previous value.
    """
    return _active_context.set(context)


def reset_active_context(token: Token[ContextProtocol | None]) -> None:
    """
    Restore the active Jobbergate context to the value it had before the token was created.
    """
    _active_context.reset(token)


@contextmanager
def active_context(context: ContextProtocol) -> Iterator[ContextProtocol]:
    """
    Context manager that sets the active Jobbergate context and restores the previous value on exit.
    """
    token = set_active_context(context)
    try:
        yield context
    finally:
        reset_active_context(token)


# ``typer.Context`` is only used for annotations; at runtime typer injects an instance of its
# vendored click ``Context`` (a base of ``typer.Context`` that does not subclass ``click.Context``),
# so all of them are detected as valid click contexts.
_CONTEXT_CLASSES: tuple[type, ...] = (click.Context, typer.Context, *typer.Context.__bases__)


def get_active_context(override: ContextProtocol | typer.Context | click.Context | None = None) -> ContextProtocol:
    """
    Get the active Jobbergate context.

    The ``override`` argument takes precedence when provided, then the value set by
    :func:`set_active_context`. A click ``Context`` may be passed as the override, in which case
    the Jobbergate context is pulled from its ``obj`` attribute. If no context is available, an
    ``Abort`` is raised, since silently creating a fresh context could hide configuration errors.
    """
    if isinstance(override, _CONTEXT_CLASSES):
        # mypy can not narrow the type from a dynamic tuple of classes, so a cast is needed
        override = cast(click.Context, override).obj

    if override is not None:
        Abort.require_condition(
            hasattr(override, "client"),
            f"Got an override of type {type(override).__name__} instead of a Jobbergate context. "
            "When calling commands directly as functions, pass all arguments as keyword arguments "
            "to avoid binding a positional value to the ``ctx`` parameter.",
            raise_kwargs=dict(subject="Invalid context override", support=True),
        )
        return cast(ContextProtocol, override)

    return Abort.enforce_defined(
        _active_context.get(),
        "No active Jobbergate context is available. When calling commands directly, either run them "
        "from within a Jobbergate CLI session or activate a context first with "
        "``with active_context(JobbergateContext()):``.",
        raise_kwargs=dict(subject="No active context", support=True),
    )
