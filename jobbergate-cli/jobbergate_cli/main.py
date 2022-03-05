import httpx
import pyperclip
import typer

from jobbergate_cli.auth import clear_token_cache, fetch_auth_tokens, init_persona, load_tokens_from_cache
from jobbergate_cli.config import settings
from jobbergate_cli.exceptions import Abort, handle_abort
from jobbergate_cli.logging import init_logs, init_sentry
from jobbergate_cli.render import terminal_message
from jobbergate_cli.schemas import JobbergateContext, Persona, TokenSet


app = typer.Typer()

if settings.JOBBERGATE_COMPATIBILITY_MODE:
    from jobbergate_cli.compat import add_legacy_compatible_commands

    add_legacy_compatible_commands(app)
else:
    from jobbergate_cli.subapps.applications.app import app as applications_app

    app.add_typer(applications_app, name="applications")

    from jobbergate_cli.subapps.job_scripts.app import app as job_scripts_app

    app.add_typer(job_scripts_app, name="job-scripts")


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


@app.command()
@handle_abort
def show_token(
    plain: bool = typer.Option(
        False,
        help="Show the token in plain text",
    ),
    refresh: bool = typer.Option(
        False,
        help="Show the refresh token instead of the access token",
    ),
    show_prefix: bool = typer.Option(
        False,
        help="Include the 'Bearer' prefix in the output",
    ),
):
    """
    Show the token for the logged in user.

    Token output is automatically copied to your clipboard.
    """
    token_set: TokenSet = load_tokens_from_cache()
    if not refresh:
        token = token_set.access_token
        subject = "Access Token"
        Abort.require_condition(
            token is not None,
            "User is not logged in. Please log in first.",
            raise_kwargs=dict(
                subject="NOT LOGGED IN",
            ),
        )
    else:
        token = token_set.refresh_token
        subject = "Refresh Token"
        Abort.require_condition(
            token is not None,
            "User is not logged in or does not have a refresh token. Please try loggin in again.",
            raise_kwargs=dict(
                subject="NO REFRESH TOKEN",
            ),
        )

    prefix = "Bearer " if show_prefix else ""
    token_text = f"{prefix}{token}"
    pyperclip.copy(token_text)
    if plain:
        print(token_text)
    else:
        terminal_message(
            token_text,
            subject=subject,
            footer="The output was copied to your clipboard",
            indent=False,
        )
