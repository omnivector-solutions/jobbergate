"""
Utilities for handling auth in jobbergate-cli.
"""

import webbrowser
from typing import Iterable

from jobbergate_core.auth.handler import DeviceCodeData
from loguru import logger
from rich.console import Console
from rich.progress import track

from jobbergate_cli.render import terminal_message
from jobbergate_cli.text_tools import copy_to_clipboard


def open_on_browser(url: str) -> bool:
    """Open the url on the browser using webbrowser."""
    try:
        browser = webbrowser.get()
        if isinstance(browser, webbrowser.GenericBrowser):
            # skip all browsers started with a command and without remote functionality
            return False
        return browser.open(url)
    except Exception as e:
        logger.warning(f"Couldn't open login url on browser due to -- {str(e)}")
        return False


def show_login_message(device_code_data: DeviceCodeData):
    """Show a message to the user with a link to the auth provider to login."""
    console = Console()
    EXTRA_CHARS = 7  # for indentation and panel borders

    verification_uri = device_code_data.verification_uri_complete
    waiting_time = int(device_code_data.expires_in / 60)

    kwargs = {}

    if open_on_browser(verification_uri):
        kwargs["footer"] = "The output was opened on your browser"
    elif copy_to_clipboard(verification_uri):
        kwargs["footer"] = "The output was copied to your clipboard"

    if console.width >= len(verification_uri) + EXTRA_CHARS:
        _show_login_standard_screen(verification_uri, waiting_time, **kwargs)
    else:
        _show_login_narrow_screen(verification_uri, waiting_time, console, **kwargs)


def _show_login_narrow_screen(verification_uri: str, waiting_time: int, console: Console, **kwargs):
    """Print the link out of the panel to make it easier to copy."""
    terminal_message(
        f"""
        To complete login, please open the link bellow in a browser.

        Waiting up to {waiting_time} minutes for you to complete the process...
        """,
        subject="Waiting for login",
        **kwargs,
    )
    console.print(verification_uri, overflow="ignore", no_wrap=True, crop=False)
    console.print()


def _show_login_standard_screen(verification_uri: str, waiting_time: int, **kwargs):
    """Print a rich panel with a link to the auth provider to login."""
    terminal_message(
        f"""
        To complete login, please open the following link in a browser:

          {verification_uri}

        Waiting up to {waiting_time} minutes for you to complete the process...
        """,
        subject="Waiting for login",
        **kwargs,
    )


def track_login_progress(iterable: Iterable) -> Iterable:
    """Track the progress of the login process on a progress bar."""
    return track(iterable, description="[green]Waiting for web login...", update_period=1, transient=True)
