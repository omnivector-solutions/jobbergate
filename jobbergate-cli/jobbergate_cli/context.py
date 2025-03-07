"""
Provides a data object for context passed from the main entry point.
"""

from dataclasses import dataclass
from functools import cached_property

from buzz import check_expressions
from httpx import Client
from jobbergate_core.auth.handler import JobbergateAuthHandler
from jobbergate_core.sdk import Apps

from jobbergate_cli.auth import show_login_message, track_login_progress
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.config import settings
from jobbergate_cli.schemas import ContextProtocol


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
            base_url=settings.ARMADA_API_BASE,
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
            raise_kwargs=dict(support=True, subject="Configuration error"),
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
