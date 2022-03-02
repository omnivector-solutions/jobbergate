import httpx
import typer

from jobbergate_cli.auth import (
    clear_token_cache,
    fetch_auth_tokens,
    init_persona,
)
from jobbergate_cli.schemas import TokenSet, Persona, JobbergateContext
from jobbergate_cli.logging import init_logs, init_sentry
from jobbergate_cli.render import terminal_message
from jobbergate_cli.exceptions import handle_abort
from jobbergate_cli.config import settings


app = typer.Typer()

if settings.JOBBERGATE_COMPATIBILITY_MODE:
    from jobbergate_cli.compat import add_legacy_compatible_commands
    add_legacy_compatible_commands(app)
else:
    from jobbergate_cli.subapps.applications.app import app as applications_app
    app.add_typer(applications_app, name="applications")


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
    persona = None

    client = httpx.Client(
        base_url=f"https://{settings.AUTH0_LOGIN_DOMAIN}",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    context = JobbergateContext(persona=None, client=client)

    if ctx.invoked_subcommand not in ("login", "logout"):
        persona = init_persona(context)
        context.client = httpx.Client(
            base_url=settings.JOBBERGATE_API_ENDPOINT,
            headers=dict(Authorization=f"Bearer {persona.token_set.access_token}"),
        )
        context.persona = persona
        context.full_output = full
        context.raw_output = raw

    ctx.obj = context


@app.command()
@handle_abort
def login(ctx: typer.Context):
    """
    Log in to the jobbergate-cli by storing the supplied token argument in the cache.
    """
    token_set: TokenSet = fetch_auth_tokens(ctx.obj)
    persona: Persona = init_persona(ctx.obj, token_set)
    terminal_message(
        f"User was logged in with email '{persona.identity_data.user_email}'",
        subject="Logged in!",
    )


@app.command()
@handle_abort
def logout():
    """
    Logs out of the jobbergate-cli. Clears the saved user credentials.
    """
    clear_token_cache()
    terminal_message(
        f"User was logged out.",
        subject="Logged out",
    )
