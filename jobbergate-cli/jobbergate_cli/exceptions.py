"""
Provide exceptions and custom handlers for the CLI.
"""

from functools import wraps

import buzz
import sentry_sdk
import typer
from loguru import logger
from rich import traceback
from rich.console import Console
from rich.panel import Panel

from jobbergate_cli.config import settings
from jobbergate_cli.constants import OV_CONTACT
from jobbergate_cli.text_tools import dedent, unwrap


# Enables prettified traceback printing via rich
traceback.install()


class JobbergateCliError(buzz.Buzz):
    """
    A generic exception base class to use in Jobbergate CLI
    """


class Abort(buzz.Buzz):
    """
    A special exception used to abort the Jobbergate CLI.

    Collects information provided for use in the ``handle_abort`` context manager.
    """

    def __init__(
        self,
        message,
        *args,
        subject=None,
        support=False,
        log_message=None,
        sentry_context=None,
        original_error=None,
        warn_only=False,
        **kwargs,
    ):
        """
        Initialize the Abort errror.
        """
        self.subject = subject
        self.support = support
        self.log_message = log_message
        self.sentry_context = sentry_context
        self.original_error = original_error
        self.warn_only = warn_only
        super().__init__(message, *args, **kwargs)


def handle_abort(func):
    """
    Apply a decorator to gracefully handle any Abort errors that happen within the context.

    Will log the error, dispatch it to Sentry, show a helpful message to the user about the error, and exit.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Abort as err:
            if not err.warn_only:
                if err.log_message is not None:
                    logger.error(err.log_message)

                if err.original_error is not None:
                    logger.error(f"Original exception: {err.original_error}")

                if settings.SENTRY_DSN:
                    with sentry_sdk.push_scope() as scope:
                        if err.sentry_context is not None:
                            scope.set_context(**err.sentry_context)
                        sentry_sdk.capture_exception(err.original_error if err.original_error is not None else err)
                        sentry_sdk.flush()

            panel_kwargs = dict()
            if err.subject is not None:
                panel_kwargs["title"] = f"[red]{err.subject}"
            message = dedent(err.message)
            if err.support:
                support_message = unwrap(
                    f"""
                    [yellow]If the problem persists,
                    please contact [bold]{OV_CONTACT}[/bold]
                    for support and trouble-shooting
                    """
                )
                message = f"{message}\n\n{support_message}"

            console = Console()
            console.print()
            console.print(Panel(message, **panel_kwargs))
            console.print()
            raise typer.Exit(code=1)

    return wrapper
