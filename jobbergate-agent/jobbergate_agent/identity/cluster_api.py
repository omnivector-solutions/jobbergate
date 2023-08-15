"""Core module for Jobbergate API identity management"""
import typing

import httpx
import jwt

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import AuthTokenError
from jobbergate_agent.utils.logging import logger


CACHE_DIR = SETTINGS.CACHE_DIR / "cluster-api"


def _load_token_from_cache() -> typing.Union[str, None]:
    """
    Looks for and returns a token from a cache file (if it exists).
    Returns None if::
    * The token does not exist
    * Can't read the token
    * The token is expired (or will expire within 10 seconds)
    """
    token_path = CACHE_DIR / "token"
    if not token_path.exists():
        return None

    try:
        token = token_path.read_text()
    except Exception:
        logger.warning(f"Couldn't load token from cache file {token_path}. Will acquire a new one")
        return None

    try:
        jwt.decode(token, options=dict(verify_signature=False, verify_exp=True), leeway=-10)
    except jwt.ExpiredSignatureError:
        logger.warning("Cached token is expired. Will acquire a new one.")
        return None

    return token


def _write_token_to_cache(token: str):
    """
    Writes the token to the cache.
    """
    if not CACHE_DIR.exists():
        logger.debug("Attempting to create missing cache directory")
        try:
            CACHE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        except Exception:
            logger.warning(f"Couldn't create missing cache directory {CACHE_DIR}. Token will not be saved.")  # noqa
            return

    token_path = CACHE_DIR / "token"
    try:
        token_path.write_text(token)
    except Exception:
        logger.warning(f"Couldn't save token to {token_path}")


def acquire_token() -> str:
    """
    Retrieves a token from OIDC based on the app settings.
    """
    logger.debug("Attempting to use cached token")
    token = _load_token_from_cache()

    if token is None:
        logger.debug("Attempting to acquire token from OIDC")
        oidc_body = dict(
            audience=SETTINGS.OIDC_AUDIENCE,
            client_id=SETTINGS.OIDC_CLIENT_ID,
            client_secret=SETTINGS.OIDC_CLIENT_SECRET,
            grant_type="client_credentials",
        )
        oidc_url = f"https://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token"
        logger.debug(f"Posting OIDC request to {oidc_url}")
        response = httpx.post(oidc_url, data=oidc_body)
        AuthTokenError.require_condition(
            response.status_code == 200,
            f"Failed to get auth token from OIDC: {response.text}",
        )
        with AuthTokenError.handle_errors("Malformed response payload from OIDC"):
            token = response.json()["access_token"]
        _write_token_to_cache(token)

    logger.debug("Successfully acquired auth token from OIDC")
    return token


class AsyncBackendClient(httpx.AsyncClient):
    """
    Extends the httpx.AsyncClient class with automatic token acquisition for requests.
    The token is acquired lazily on the first httpx request issued.
    This client should be used for most agent actions.
    """

    _token: typing.Optional[str]

    def __init__(self):
        self._token = None
        super().__init__(
            base_url=SETTINGS.BASE_API_URL,
            auth=self._inject_token,
            event_hooks=dict(
                request=[self._log_request],
                response=[self._log_response],
            ),
        )

    def _inject_token(self, request: httpx.Request) -> httpx.Request:
        if self._token is None:
            self._token = acquire_token()
        request.headers["authorization"] = f"Bearer {self._token}"
        return request

    @staticmethod
    async def _log_request(request: httpx.Request):
        logger.debug(f"Making request: {request.method} {request.url}")

    @staticmethod
    async def _log_response(response: httpx.Response):
        logger.debug(
            f"Received response: {response.request.method} " f"{response.request.url} " f"{response.status_code}"
        )


backend_client = AsyncBackendClient()
