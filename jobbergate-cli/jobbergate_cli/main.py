"""
Provide main entry point for the Jobbergate CLI App.
"""

import sys
from typing import Any

import importlib_metadata
import typer

from jobbergate_cli.config import settings
from jobbergate_cli.context import JobbergateContext
from jobbergate_cli.exceptions import Abort, handle_abort, handle_authentication_error
from jobbergate_cli.logging import init_logs, init_sentry
from jobbergate_cli.render import render_demo, render_json, terminal_message
from jobbergate_cli.schemas import ContextProtocol
from jobbergate_cli.subapps.applications.app import app as applications_app
from jobbergate_cli.subapps.job_scripts.app import app as job_scripts_app
from jobbergate_cli.subapps.job_submissions.app import app as job_submissions_app
from jobbergate_cli.text_tools import copy_to_clipboard

app = typer.Typer()


# If "compatibility" mode is set through the environment, map the commands at their familiar placement on the main app.
if settings.JOBBERGATE_COMPATIBILITY_MODE:
    from jobbergate_cli.compat import add_legacy_compatible_commands

    add_legacy_compatible_commands(app)

app.add_typer(applications_app, name="applications")
app.add_typer(job_scripts_app, name="job-scripts")
app.add_typer(job_submissions_app, name="job-submissions")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, help="Enable verbose logging to the terminal"),
    full: bool = typer.Option(False, help="Print all fields from CRUD commands"),
    raw: bool = typer.Option(False, help="Print output from CRUD commands as raw json"),
    version: bool = typer.Option(False, help="Print the version of jobbergate-cli and exit"),
    ignore_extra_args: str = typer.Option(
        None,
        "--username",
        "-u",
        "--password",
        "-p",
        hidden=True,
        help="Ignore extra arguments passed to the command for backward compatibility with the legacy app.",
    ),
):
    """
    Welcome to the Jobbergate CLI!

    More information can be shown for each command listed below by running it with the --help option.
    """
    if version:
        typer.echo(importlib_metadata.version("jobbergate-cli"))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        render_demo(pre_amble="No command provided.")
        raise typer.Exit()

    init_logs(verbose=verbose)
    init_sentry()

    # Stored first as a local variable to enable type checking and make mypy happy with the syntax
    # Then stored in the context object to be passed to the subcommands
    context: ContextProtocol = JobbergateContext(full_output=full, raw_output=raw)
    ctx.obj = context


@app.command(rich_help_panel="Authentication")
def login(ctx: typer.Context):
    """
    Log in to the jobbergate-cli by storing the supplied token argument in the cache.
    """
    ctx.obj.authentication_handler.login()
    identity_data = ctx.obj.authentication_handler.get_identity_data()
    terminal_message(f"User was logged in with email '{identity_data.email}'", subject="Logged in!")
    render_demo()


@app.command(rich_help_panel="Authentication")
def logout(ctx: typer.Context):
    """
    Logs out of the jobbergate-cli. Clears the saved user credentials.
    """
    ctx.obj.authentication_handler.logout()
    terminal_message("User was logged out.", subject="Logged out")


@app.command(rich_help_panel="Authentication")
def show_token(
    ctx: typer.Context,
    plain: bool = typer.Option(
        False,
        help="Show the token in plain text.",
    ),
    refresh: bool = typer.Option(
        False,
        help="Show the refresh token instead of the access token.",
    ),
    show_prefix: bool = typer.Option(
        False,
        "--prefix",
        help="Include the 'Bearer' prefix in the output.",
    ),
    show_header: bool = typer.Option(
        False,
        "--header",
        help="Show the token as it would appear in a request header.",
    ),
    decode: bool = typer.Option(
        False,
        "--decode",
        help="Show the content of the decoded access token.",
    ),
):
    """
    Show the token for the logged in user.

    Token output is automatically copied to your clipboard.
    """
    ctx.obj.authentication_handler.acquire_access()
    if refresh:
        token = ctx.obj.authentication_handler._refresh_token
    else:
        token = ctx.obj.authentication_handler._access_token

    Abort.require_condition(token.is_valid(), f"Could not obtain {token.label}. Please try loggin in again.")

    if decode:
        # Decode the token with ALL verification turned off (we just want to unpack it)
        render_json(token.data)
        return

    if show_header:
        token_text = f"""{{ "Authorization": "{token.bearer_token}" }}"""
    elif show_prefix:
        token_text = token.bearer_token
    else:
        token_text = token.content

    on_clipboard = copy_to_clipboard(token_text)

    if plain:
        print(token_text)
    else:
        subject = f"{token.label.title()} Token"
        kwargs: dict[str, Any] = dict(subject=subject, indent=False)
        if on_clipboard:
            kwargs["footer"] = "The output was copied to your clipboard"

        terminal_message(token_text, **kwargs)


def safe_entrypoint():
    """
    Entrypoint for the app including custom error handling.

    With this we ensure error handling is applied to all commands with no need
    to duplicate the decorators on each of them.
    """
    try:
        safe_function = handle_abort(handle_authentication_error(app.__call__))
        safe_function()
    except typer.Exit as e:
        sys.exit(e.exit_code)
