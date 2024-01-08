"""Core module for Jobbergate API clients management"""

import typing
from datetime import datetime, timedelta

import httpx
import sentry_sdk
from buzz import enforce_defined
from jobbergate_core.auth.token import Token, TokenError
from jose import jwt

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import logger


CACHE_DIR = SETTINGS.CACHE_DIR / "slurmrestd"


def acquire_token(username: str) -> str:
    """
    Retrieves a token from Slurmrestd based on the app settings.
    """
    logger.debug("Attempting to use cached token")
    base_token = Token(cache_directory=CACHE_DIR, label=username)

    try:
        token = base_token.load_from_cache()
        if token.is_valid():
            return token.content
    except TokenError as e:
        logger.debug("Failed to load token from cache: {}", e)

    logger.debug("Attempting to generate token for Slurmrestd")

    if SETTINGS.SLURMRESTD_USE_KEY_PATH and SETTINGS.SLURMRESTD_JWT_KEY_PATH:
        secret_key = open(SETTINGS.SLURMRESTD_JWT_KEY_PATH, "r").read()
    else:
        secret_key = enforce_defined(
            SETTINGS.SLURMRESTD_JWT_KEY_STRING,
            "SLURMRESTD_JWT_KEY_STRING is not defined",
        )

    now = datetime.now()
    payload = {
        "exp": int(datetime.timestamp(now + timedelta(seconds=SETTINGS.SLURMRESTD_EXP_TIME_IN_SECONDS))),
        "iat": int(datetime.timestamp(now)),
        "sun": username,
    }
    token_content = jwt.encode(payload, secret_key, algorithm="HS256")

    token = base_token.replace(content=token_content)
    token.cache_directory.mkdir(parents=True, exist_ok=True)
    token.save_to_cache()

    logger.debug("Successfully generated auth token")
    return token.content


def inject_token(
    request: httpx.Request,
    username: typing.Optional[str] = None,
) -> httpx.Request:
    """
    Inject a token based on the provided username into the request.

    For requests that need to use something except the default username,
    this injector should be used at the request level (instead of at client
    initialization) like this:

    .. code-block:: python

       client.get(url, auth=lambda r: inject_token(r, username=username))
    """
    if username is None:
        username = SETTINGS.X_SLURM_USER_NAME

    token = SETTINGS.X_SLURM_USER_TOKEN
    if token is None:
        token = acquire_token(username)

    request.headers["x-slurm-user-name"] = username
    request.headers["x-slurm-user-token"] = token
    return request


class AsyncBackendClient(httpx.AsyncClient):
    """
    Extends the httpx.AsyncClient class with automatic token acquisition for requests.
    The token is acquired lazily on the first httpx request issued.
    This client should be used for most agent actions.
    """

    _token: typing.Optional[str]

    def __init__(self):
        if SETTINGS.SLURM_RESTD_VERSIONED_URL is None:
            raise ValueError("SLURM_RESTD_VERSIONED_URL must be set in order to use the AsyncBackendClient")
        super().__init__(
            base_url=SETTINGS.SLURM_RESTD_VERSIONED_URL,
            auth=inject_token,
            event_hooks=dict(
                request=[self._log_request],
                response=[self._log_response],
            ),
            timeout=SETTINGS.REQUESTS_TIMEOUT,
        )

    @staticmethod
    async def _log_request(request: httpx.Request):
        logger.debug(f"Making request: {request.method} {request.url}")

    @staticmethod
    async def _log_response(response: httpx.Response):
        logger.debug(
            f"Received response: {response.request.method} " f"{response.request.url} " f"{response.status_code}"
        )

    async def request(self, *args, **kwargs):
        """
        Request wrapper that captures request errors and sends them to Sentry.

        This ensures events are sent to Sentry even if the caller handles the exception.
        """
        try:
            return await super().request(*args, **kwargs)
        except Exception as err:
            sentry_sdk.capture_exception(err)
            logger.error(f"Request to Slurm-API failed: {err}")
            raise err


backend_client = AsyncBackendClient()
