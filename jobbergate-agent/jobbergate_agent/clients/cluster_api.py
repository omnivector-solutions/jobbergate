"""Core module for Jobbergate API clients management"""

import httpx
import sentry_sdk
from jobbergate_core.auth.token import Token, TokenError, TokenType

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import AuthTokenError
from jobbergate_agent.utils.logging import logger


CACHE_DIR = SETTINGS.CACHE_DIR / "cluster-api"


def acquire_token(token: Token) -> Token:
    """
    Retrieves a token from OIDC based on the app settings.
    """
    try:
        new_token = token.load_from_cache()
        if new_token.is_valid():
            return new_token
    except TokenError as e:
        logger.debug("Failed to load token from cache: {}", e)

    logger.debug("Attempting to acquire token from OIDC")
    oidc_body = dict(
        client_id=SETTINGS.OIDC_CLIENT_ID,
        client_secret=SETTINGS.OIDC_CLIENT_SECRET,
        grant_type="client_credentials",
    )
    protocol = "https" if SETTINGS.OIDC_USE_HTTPS else "http"
    oidc_url = f"{protocol}://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token"
    logger.debug(f"Posting OIDC request to {oidc_url}")

    with httpx.Client() as client:
        response = client.post(oidc_url, data=oidc_body)

    AuthTokenError.require_condition(
        response.status_code == 200,
        f"Failed to get auth token from OIDC: {response.text}",
    )
    with AuthTokenError.handle_errors("Malformed response payload from OIDC"):
        new_token_content = response.json()["access_token"]

    new_token = token.replace(content=new_token_content)
    new_token.cache_directory.mkdir(parents=True, exist_ok=True)
    new_token.save_to_cache()

    logger.debug("Successfully acquired auth token from OIDC")
    return new_token


class AsyncBackendClient(httpx.AsyncClient):
    """
    Extends the httpx.AsyncClient class with automatic token acquisition for requests.
    The token is acquired lazily on the first httpx request issued.
    This client should be used for most agent actions.
    """

    _token: Token

    def __init__(self):
        self._token = Token(
            cache_directory=CACHE_DIR,
            label=TokenType.ACCESS,
        )
        super().__init__(
            base_url=SETTINGS.BASE_API_URL,
            auth=self._inject_token,
            event_hooks=dict(
                request=[self._log_request],
                response=[self._log_response],
            ),
            timeout=SETTINGS.REQUESTS_TIMEOUT,
        )

    def _inject_token(self, request: httpx.Request) -> httpx.Request:
        if not self._token.is_valid():
            self._token = acquire_token(self._token)
        request.headers["authorization"] = self._token.bearer_token
        return request

    @staticmethod
    async def _log_request(request: httpx.Request):
        logger.debug(f"Making request: {request.method} {request.url}")

    @staticmethod
    async def _log_response(response: httpx.Response):
        logger.debug(f"Received response: {response.request.method} {response.request.url} {response.status_code}")

    async def request(self, *args, **kwargs):
        """
        Request wrapper that captures request errors and sends them to Sentry.

        This ensures events are sent to Sentry even if the caller handles the exception.
        """
        try:
            return await super().request(*args, **kwargs)
        except Exception as err:
            sentry_sdk.capture_exception(err)
            logger.error(f"Request to Jobbergate-API failed: {err}")
            raise err


backend_client = AsyncBackendClient()
