"""
Utilities for handling auth in jobbergate-cli.
"""
from time import sleep
from typing import Optional, Type, TypeVar

import httpx
import pydantic
import snick
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from loguru import logger

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.config import settings
from jobbergate_cli.cli_helpers import terminal_message
from jobbergate_cli.time_loop import TimeLoop
from jobbergate_cli.schemas import TokenSet, IdentityData, Persona, DeviceCodeData, JobbergateContext
from jobbergate_cli.crud_helpers import make_request


def validate_token_and_extract_identity(token_set: TokenSet) -> IdentityData:
    """
    Validate the access_token from a TokenSet and extract the identity data.

    Validations:
        * Checks timestamp on the access token.
        * Checks for identity data
        * Checks that all identity elements are present

    Reports an error in the logs and to the user if there is an issue with the access_token
    """
    logger.debug("Validating access token")
    try:
        token_data = jwt.decode(
            token_set.access_token,
            None,
            options=dict(
                verify_signature=False,
                verify_aud=False,
                verify_exp=True,
            ),
        )
    except ExpiredSignatureError:
        raise  # Will be handled in calling context
    except Exception as err:
        raise Abort(
            """
            There was an unknown error while validating the access token.

            Please try logging in again.
            """,
            subject="INVALID ACCESS TOKEN",
            support=True,
            log_message=f"Unknown error while validating access access token: {err}",
            sentry_context=dict(access_token=dict(access_token=token_set.access_token)),
            original_error=err,
        )

    logger.debug("Extracting identity data from the access token")
    identity_claims = token_data.get(settings.IDENTITY_CLAIMS_KEY)
    Abort.require_condition(
        identity_claims,
        "No identity data found in access token data",
        raise_kwargs=dict(
            subject="NO IDENTITY FOUND",
            support=True,
        ),
    )
    try:
        return IdentityData.parse_obj(identity_claims)
    except pydantic.ValidationError as err:
        raise Abort(
            """
            The identity data in the access token is malformed or incomplete.

            Please try logging in again.
            """,
            subject="INVALID IDENTITY DATA",
            support=True,
            log_message=f"Identity data is incomplete: {err}",
            sentry_context=dict(access_token=dict(access_token=token_set.access_token)),
        )


def load_tokens_from_cache() -> TokenSet:
    """
    Loads an access token (and a refresh token if one exists) from the cache.
    """
    Abort.require_condition(
        settings.JOBBERGATE_API_ACCESS_TOKEN_PATH.exists(),
        "Please login with your auth token first using the `jobbergate login` command",
        raise_kwargs=dict(subject="YOU NEED TO LOGIN"),
    )

    logger.debug("Retrieving access token from cache")
    token_set = TokenSet(access_token=settings.JOBBERGATE_API_ACCESS_TOKEN_PATH.read_text())

    if settings.JOBBERGATE_API_REFRESH_TOKEN_PATH.exists():
        logger.debug("Retrieving refresh token from cache")
        token_set.refresh_token = settings.JOBBERGATE_API_REFRESH_TOKEN_PATH.read_text()

    return token_set


def save_tokens_to_cache(token_set: TokenSet):
    """
    Saves tokens from a token_set to the cache.
    """
    logger.debug(f"Caching access token at {settings.JOBBERGATE_API_ACCESS_TOKEN_PATH}")
    settings.JOBBERGATE_API_ACCESS_TOKEN_PATH.write_text(token_set.access_token)

    if token_set.refresh_token is not None:
        logger.debug(f"Caching refresh token at {settings.JOBBERGATE_API_REFRESH_TOKEN_PATH}")
        settings.JOBBERGATE_API_REFRESH_TOKEN_PATH.write_text(token_set.refresh_token)


def clear_token_cache():
    """
    Clears the token cache.
    """
    logger.debug("Clearing cached tokens")

    logger.debug(f"Removing access token at {settings.JOBBERGATE_API_ACCESS_TOKEN_PATH}")
    if settings.JOBBERGATE_API_ACCESS_TOKEN_PATH.exists():
        settings.JOBBERGATE_API_ACCESS_TOKEN_PATH.unlink()

    logger.debug(f"Removing refresh token at {settings.JOBBERGATE_API_REFRESH_TOKEN_PATH}")
    if settings.JOBBERGATE_API_REFRESH_TOKEN_PATH.exists():
        settings.JOBBERGATE_API_REFRESH_TOKEN_PATH.unlink()


def init_persona(token_set: Optional[TokenSet] = None):
    """
    Initializes the "persona" which contains the tokens and identity data for a user.

    Retrieves the access token for the user from the cache.

    Token is retrieved from the cache, validated, and identity data is extracted.

    If the access token is expired, a new one will be acquired via the cached refresh token (if there is one).

    Saves token_set to cache.

    Returns the persona.
    """
    if token_set is None:
        token_set = load_tokens_from_cache()

    try:
        identity_data = validate_token_and_extract_identity(token_set)
    except ExpiredSignatureError:
        Abort.require_condition(
            token_set.refresh_token is not None,
            "The auth token is expired. Please retrieve a new and log in again.",
            raise_kwargs=dict(
                subject="EXPIRED ACCESS TOKEN",
                support=True,
            ),
        )

        logger.debug("The access token is expired. Attempting to refresh token")
        refresh_access_token(token_set)
        identity_data = validate_token_and_extract_identity(token_set)

    logger.debug(f"Persona created with identity data: {identity_data}")

    save_tokens_to_cache(token_set)

    return Persona(
        token_set=token_set,
        identity_data=identity_data,
    )


def refresh_access_token(ctx: JobbergateContext, token_set: TokenSet):
    """
    Attempt to fetch a new access token given a refresh token in a token_set.

    Sets the access token in-place.

    If refresh fails, notify the user that they need to log in again.
    """
    url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    logger.debug(f"Requesting refreshed access token from {url}")

    # Make mypy happy
    assert ctx.client is not None

    refreshed_token_set = make_request(
        ctx.client,
        "/oauth/token",
        "POST",
        abort_message="The auth token could not be refreshed. Please try logging in again.",
        abort_subject="EXPIRED ACCESS TOKEN",
        support=True,
        response_model=TokenSet,
        request_kwargs=dict(
            client_id=settings.AUTH0_CLIENT_ID,
            audience=settings.AUTH0_AUDIENCE,
            grant_type="refresh_token",
            refresh_token=token_set.refresh_token,
        ),
    )

    # Make mypy happy
    assert isinstance(refreshed_token_set, TokenSet)
    token_set.access_token = refreshed_token_set.access_token


ResponseModel = TypeVar('ResponseModel', bound=pydantic.BaseModel)


def _fetch_and_unpack(
    url_path: str,
    params: dict,
    user_error_message: str,
    user_error_subject: str,
    abort_not_ok: bool,
    response_model: Type[ResponseModel],
) -> Optional[ResponseModel]:
    """
    Fetch data from the auth provider URL and unpack it into a response model.
    Should not be used outside of the ``auth`` module.
    """
    url = f"https://{settings.AUTH0_DOMAIN}{url_path}"
    logger.debug(f"Posting request to auth provider at {url} with {params=}")
    response = httpx.post(
        url,
        headers={"content-type": "application/x-www-form-urlencoded"},
        data=params,
    )

    logger.debug("Extracting json data from response")
    try:
        data = response.json()
    except Exception as err:
        raise Abort(
            snick.unwrap(
                f"""
                {user_error_message}:
                Response carried no data.
                """
            ),
            subject=user_error_subject,
            support=True,
            log_message=f"Failed unpacking json ({response.status_code}): {response.text}",
            original_error=err,
        )
    logger.debug(f"Response from request: {data}")

    logger.debug(f"Checking response status code: {response.status_code}")
    if response.status_code != 200:
        if abort_not_ok:
            raise Abort(
                snick.unwrap(
                    f"""
                    {user_error_message}:
                    Received an error response.
                    """
                ),
                subject=user_error_subject,
                support=True,
                log_message=f"Got an error response code ({response.status_code}): {response.text}",
            )
        else:
            return None

    logger.debug("Validating response data with ResponseModel")
    try:
        return response_model(**data)
    except pydantic.ValidationError as err:
        raise Abort(
            snick.unwrap(
                f"""
                {user_error_message}:
                Unexpected data in response.
                """
            ),
            subject=user_error_subject,
            support=True,
            log_message=f"Unexpeced format in response data: {data}",
            original_error=err,
        )


def fetch_auth_tokens(ctx: JobbergateContext) -> TokenSet:
    """
    Fetch an access token (and possibly a refresh token) from Auth0.

    Prints out a URL for the user to use to authenticate and polls the token endpoint to fetch it when
    the browser-based process finishes
    """
    device_code_data = _fetch_and_unpack(
        url_path="/oauth/device/code",
        params=dict(
            client_id=settings.AUTH0_CLIENT_ID,
            audience=settings.AUTH0_AUDIENCE,
            scope="offline_access",  # To get refresh token
        ),
        user_error_message="There was a problem retrieving a device verification code from the auth provider",
        user_error_subject="COULD NOT RETRIEVE TOKEN",
        abort_not_ok=True,
        response_model=DeviceCodeData,
    )

    # make mypy happy
    assert ctx.client is not None

    device_code_data = make_request(
        ctx.client,
        "/oauth/token",
        "POST",
        abort_message="There was a problem retrieving a device verification code from the auth provider",
        abort_subject="COULD NOT RETRIEVE TOKEN",
        support=True,
        response_model=DeviceCodeData,
        data=dict(
            client_id=settings.AUTH0_CLIENT_ID,
            audience=settings.AUTH0_AUDIENCE,
            scope="offline_access",  # To get refresh token
        ),
    )

    # Make mypy happy (this will never be None)
    assert device_code_data is not None

    terminal_message(
        f"""
        To complete login, please open the following link in a browser:

          {device_code_data.verification_uri_complete}

        Waiting up to {settings.AUTH0_MAX_POLL_TIME / 60} minutes for you to complete the process...
        """,
        subject="Waiting for login",
    )

    for tick in TimeLoop(
        settings.AUTH0_MAX_POLL_TIME,
        message="Waiting for web login",
    ):
        # YOU LEFT OFF HERE, DUMBASS
        token_set = _fetch_and_unpack(
            url_path="/oauth/token",
            params=dict(
                grant_type="urn:ietf:params:oauth:grant-type:device_code",
                device_code=device_code_data.device_code,
                client_id=settings.AUTH0_CLIENT_ID,
            ),
            user_error_message="There was a problem retrieving your access token from the auth provider",
            user_error_subject="COULD NOT FETCH ACCESS TOKEN",
            abort_not_ok=False,
            response_model=TokenSet,
        )
        if token_set is not None:
            # Make mypy happy
            assert isinstance(token_set, TokenSet)
            return token_set

        logger.debug(f"Token fetch attempt #{tick.counter} failed")
        sleep(device_code_data.interval)

    raise Abort(
        "Login process was not completed in time. Please try again.",
        subject="TIMED OUT",
        log_message="Timed out while waiting for user to complete login"
    )
