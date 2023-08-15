"""Core module for Jobbergate API identity management"""

import typing
from datetime import datetime, timedelta

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import logger


CACHE_DIR = SETTINGS.CACHE_DIR / "slurmrestd"


def _load_token_from_cache(username: str) -> typing.Union[str, None]:
    """
    Looks for and returns a token from a cache file (if it exists).
    Returns None if::
    * The token does not exist
    * Can't read the token
    * The token is expired (or will expire within 10 seconds)
    * The token has invalid signature
    * The token has invalid claims
    """
    token_path = CACHE_DIR / f"{username}.token"
    logger.debug(f"Attempting to retrieve token from: {token_path}")
    if not token_path.exists():
        logger.debug("Cached token does not exist")
        return None

    try:
        token = token_path.read_text().strip()
        logger.debug(f"Retrieved token from {token_path} as {token}")
    except Exception:
        logger.warning(f"Couldn't load token from cache file {token_path}. Will acquire a new one")
        return None

    if SETTINGS.SLURMRESTD_USE_KEY_PATH:
        secret_key = open(SETTINGS.SLURMRESTD_JWT_KEY_PATH, "r").read()
    else:
        secret_key = SETTINGS.SLURMRESTD_JWT_KEY_STRING

    try:
        jwt.decode(token, secret_key, options=dict(verify_signature=False, verify_exp=True, leeway=-10))
    except ExpiredSignatureError:
        logger.warning("Cached token is expired. Will acquire a new one.")
        return None
    except JWTClaimsError:
        logger.warning("Cached token has the signature invalid in any way. Will acquire a new one.")
        return None
    except JWTError:
        logger.warning("Cached token has invalid claims. Will acquire a new one.")
        return None

    return token


def _write_token_to_cache(token: str, username: str):
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

    token_path = CACHE_DIR / f"{username}.token"
    try:
        token_path.write_text(token)
    except Exception:
        logger.warning(f"Couldn't save token to {token_path}")


def acquire_token(username: str) -> str:
    """
    Retrieves a token from Slurmrestd based on the app settings.
    """
    logger.debug("Attempting to use cached token")
    token = _load_token_from_cache(username)

    if token is None:
        logger.debug("Attempting to generate token for Slurmrestd")
        if SETTINGS.SLURMRESTD_USE_KEY_PATH:
            secret_key = open(SETTINGS.SLURMRESTD_JWT_KEY_PATH, "r").read()
        else:
            secret_key = SETTINGS.SLURMRESTD_JWT_KEY_STRING

        now = datetime.now()
        payload = {
            "exp": int(datetime.timestamp(now + timedelta(seconds=SETTINGS.SLURMRESTD_EXP_TIME_IN_SECONDS))),
            "iat": int(datetime.timestamp(now)),
            "sun": username,
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        _write_token_to_cache(token, username)

    logger.debug("Successfully generated auth token")
    return token


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
        )

    @staticmethod
    async def _log_request(request: httpx.Request):
        logger.debug(f"Making request: {request.method} {request.url}")

    @staticmethod
    async def _log_response(response: httpx.Response):
        logger.debug(
            f"Received response: {response.request.method} " f"{response.request.url} " f"{response.status_code}"
        )


backend_client = AsyncBackendClient()
