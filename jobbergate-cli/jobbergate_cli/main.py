import typing

import httpx
import typer

from jobbergate_cli.auth import (
    clear_token_cache,
    fetch_auth_tokens,
    init_persona,
)
from jobbergate_cli.schemas import TokenSet, Persona, JobbergateContext
from jobbergate_cli.constants import SortOrder
from jobbergate_cli.logging import init_logs, init_sentry
from jobbergate_cli.cli_helpers import terminal_message
from jobbergate_cli import applications
from jobbergate_cli.exceptions import handle_abort
from jobbergate_cli.config import settings


app = typer.Typer()


@app.callback()
@handle_abort
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, help="Enable verbose logging to the terminal"),
    full: bool = typer.Option(False, help="Print all fields from CRUD commands"),
    raw: bool = typer.Option(False, help="Print output from CRUD commands as raw json"),
):
    """
    Welcome to the Jobbergate CLI!

    More information can be shown for each command listed below by running it with the --help option.
    """
    init_logs(verbose=verbose)
    init_sentry()
    if ctx.invoked_subcommand not in ("login", "logout"):
        persona = init_persona()
        client=httpx.Client(
            base_url=settings.JOBBERGATE_API_ENDPOINT,
            headers=dict(Authorization=f"Bearer {persona.token_set.access_token}"),
        )
    else:
        persona = None
        client=httpx.Client(
            base_url=f"https://{settings.AUTH0_DOMAIN}",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

    ctx.obj = JobbergateContext(
        persona=persona,
        full_output=full,
        raw_output=raw,
        client=client,
    )


@app.command()
def login(ctx: typer.Context):
    """
    Log in to the jobbergate-cli by storing the supplied token argument in the cache.
    """
    token_set: TokenSet = fetch_auth_tokens(ctx.obj)
    persona: Persona = init_persona(token_set)
    terminal_message(
        f"User was logged in with email '{persona.identity_data.user_email}'",
        subject="Logged in!",
    )


@app.command()
def logout():
    """
    Logs out of the jobbergate-cli. Clears the saved user credentials.
    """
    clear_token_cache()
    terminal_message(
        f"User was logged out.",
        subject="Logged out",
    )



# Should figure out how to move the sub-commands into the other modules....later
@app.command()
@handle_abort
def list_applications(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all applications, even the ones without identifier"),
    user_only: bool = typer.Option(False, "--user", help="Show only applications owned by the current user"),
    search: typing.Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.UNSORTED, help="Specify sort order"),
    sort_field: typing.Optional[str] = typer.Option(None, help="The field by which results should be sorted"),
):
    applications.list_applications(
        ctx.obj,
        show_all,
        user_only,
        search,
        sort_order,
        sort_field,
    )


@app.command()
@handle_abort
def get_application(
    ctx: typer.Context,
    id: typing.Optional[int] = typer.Option(
        None,
        help=f"The specific id of the application. {applications.ID_NOTE}",
    ),
    identifier: typing.Optional[str] = typer.Option(
        None,
        help=f"The human-friendly identifier of the application. {applications.IDENTIFIER_NOTE}",
    ),
):
    applications.get_application(
        ctx.obj,
        id,
        identifier,
    )
