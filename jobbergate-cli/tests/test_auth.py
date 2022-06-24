from pathlib import Path

import httpx
import pendulum
import plummet
import pytest
from jose import ExpiredSignatureError, jwt

from jobbergate_cli.auth import (
    TokenSet,
    clear_token_cache,
    fetch_auth_tokens,
    init_persona,
    load_tokens_from_cache,
    refresh_access_token,
    save_tokens_to_cache,
    validate_token_and_extract_identity,
)
from jobbergate_cli.config import settings
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.time_loop import Tick


LOGIN_DOMAIN = "https://dummy-auth.com"


@pytest.fixture
def dummy_context():
    return JobbergateContext(
        persona=None,
        client=httpx.Client(base_url=LOGIN_DOMAIN, headers={"content-type": "application/x-www-form-urlencoded"}),
    )


@pytest.fixture
def make_token():
    """
    Provide a fixture that returns a helper function for creating an access_token for testing.
    """

    def _helper(azp: str = None, email: str = None, expires=plummet.AGGREGATE_TYPE) -> str:
        """
        Create an access_token with a given user email, org name, and expiration moment.
        """
        expires_moment: pendulum.DateTime = plummet.momentize(expires)

        extra_claims = dict()
        if azp is not None:
            extra_claims["azp"] = azp
        if email is not None:
            extra_claims["email"] = email

        return jwt.encode(
            {
                "exp": expires_moment.int_timestamp,
                **extra_claims,
            },
            "fake-secret",
            algorithm="HS256",
        )

    return _helper


def test_validate_token_and_extract_identity__success(make_token):
    """
    Validate that the ``validate_token_and_extract_identity()`` function can successfully validate a good
    access token and extract the user's identity from it.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    with plummet.frozen_time("2022-02-16 21:30:00"):
        identity_data = validate_token_and_extract_identity(TokenSet(access_token=access_token))
    assert identity_data.client_id == "dummy-client"
    assert identity_data.email == "good@email.com"


def test_validate_token_and_extract_identity__re_raises_ExpiredSignatureError(make_token):
    """
    Validate that the ``validate_token_and_extract_identity()`` function will catch and then re-raise a
    ``ExpiredSignatureError`` thrown by the ``jwt.decode()`` function.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 20:30:00",
    )
    with plummet.frozen_time("2022-02-16 21:30:00"):
        with pytest.raises(ExpiredSignatureError):
            validate_token_and_extract_identity(TokenSet(access_token=access_token))


def test_validate_token_and_extract_identity__raises_abort_on_empty_token():
    """
    Validate that the ``validate_token_and_extract_identity()`` function will
    raise an ``Abort`` when the access_token exists but is an empty string/file.
    """
    test_token_set = TokenSet(access_token="")
    with pytest.raises(Abort, match="Access token file exists but it is empty"):
        validate_token_and_extract_identity(test_token_set)


def test_validate_token_and_extract_identity__raises_abort_on_unknown_error(mocker):
    """
    Validate that the ``validate_token_and_extract_identity()`` function will raise an ``Abort`` when the
    ``jwt.decode()`` function raises an exception type besides ``ExpiredSignatureError``.
    """
    test_token_set = TokenSet(access_token="BOGUS-TOKEN")
    mocker.patch("jose.jwt.decode", side_effect=Exception("BOOM!"))
    with pytest.raises(Abort, match="There was an unknown error while validating"):
        validate_token_and_extract_identity(test_token_set)


def test_validate_token_and_extract_identity__raises_abort_if_token_is_missing_identity_data(make_token):
    """
    Validate that the ``validate_token_and_extract_identity()`` function will raise an Abort if the
    access_token doesn't carry all the required identity data in it.
    """
    access_token = make_token(expires="2022-02-16 22:30:00")
    with plummet.frozen_time("2022-02-16 21:30:00"):
        with pytest.raises(Abort, match="error extracting the user's identity"):
            validate_token_and_extract_identity(TokenSet(access_token=access_token))


def test_load_tokens_from_cache__success(make_token, tmp_path, mocker):
    """
    Validate that the ``load_tokens_from_cache()`` function can successfully load tokens from the token
    cache on disk.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    access_token_path.write_text(access_token)
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"
    refresh_token_path.write_text(refresh_token)

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    token_set = load_tokens_from_cache()

    assert token_set.access_token == access_token
    assert token_set.refresh_token == refresh_token


def test_load_tokens_from_cache__raises_abort_if_access_token_path_does_not_exist(mocker):
    """
    Validate taht the ``load_tokens_from_cache()`` function raises an Abort if the token does not exist
    at the location specified by ``settings.JOBBERGATE_ACCESS_TOKEN_PATH``.
    """
    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=Path("/some/fake/path"))
    with pytest.raises(Abort, match="login with your auth token first"):
        load_tokens_from_cache()


def test_load_tokens_from_cache__omits_refresh_token_if_it_is_not_found(make_token, tmp_path, mocker):
    """
    Validate that the ``load_tokens_from_cache()`` function can successfully create a token set without the
    refresh token if the location specified by ``settings.JOBBERGATE_REFRESH_TOKEN_PATH`` does not exist.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    access_token_path.write_text(access_token)

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=Path("/some/fake/path"))
    token_set = load_tokens_from_cache()

    assert token_set.access_token == access_token
    assert token_set.refresh_token is None


def test_save_tokens_to_cache__success(make_token, tmp_path, mocker):
    """
    Validate that the ``save_tokens_to_cache()`` function will write a access and refresh token from a
    ``TokenSet`` instance to the locations described by ``JOBBERGATE_ACCESS_TOKEN_PATH`` and
    ``JOBBERGATE_REFRESH_TOKEN_PATH``.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"
    token_set = TokenSet(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    save_tokens_to_cache(token_set)

    assert access_token_path.exists()
    assert access_token_path.read_text() == access_token

    assert refresh_token_path.exists()
    assert refresh_token_path.read_text() == refresh_token


def test_save_tokens_to_cache__only_saves_access_token_if_refresh_token_is_not_defined(make_token, tmp_path, mocker):
    """
    Validate that the ``save_tokens_to_cache()`` function will only write an access token to the cache if the
    ``TokenSet`` instance does not carry a refresh token.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    refresh_token_path = tmp_path / "refresh.jwt"
    token_set = TokenSet(
        access_token=access_token,
    )

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    save_tokens_to_cache(token_set)

    assert access_token_path.exists()
    assert access_token_path.read_text() == access_token

    assert not refresh_token_path.exists()


def test_clear_token_cache__success(make_token, tmp_path, mocker):
    """
    Validate that the ``clear_token_cache()`` function removes the access token and refresh token from the
    cache.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    access_token_path.write_text(access_token)
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"
    refresh_token_path.write_text(refresh_token)

    assert access_token_path.exists()
    assert refresh_token_path.exists()

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    clear_token_cache()

    assert not access_token_path.exists()


def test_clear_token_cache__does_not_fail_if_no_tokens_are_in_cache(tmp_path, mocker):
    """
    Validate that the ``clear_token_cache()`` function does not fail if there are no tokens in the cache.
    """
    access_token_path = tmp_path / "access.jwt"
    refresh_token_path = tmp_path / "refresh.jwt"

    assert not access_token_path.exists()
    assert not refresh_token_path.exists()

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    clear_token_cache()


def test_init_persona__success(make_token, tmp_path, dummy_context, mocker):
    """
    Validate that the ``init_persona()`` function will load tokens from the cache, validate them,
    extract user email, and return a new ``Persona`` instance with the tokens and user email contained
    within it.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    access_token_path.write_text(access_token)
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"
    refresh_token_path.write_text(refresh_token)

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    with plummet.frozen_time("2022-02-16 21:30:00"):
        persona = init_persona(dummy_context)

    assert persona.token_set.access_token == access_token
    assert persona.token_set.refresh_token == refresh_token
    assert persona.identity_data.client_id == "dummy-client"
    assert persona.identity_data.email == "good@email.com"


def test_init_persona__uses_passed_token_set(make_token, tmp_path, dummy_context, mocker):
    """
    Validate that the ``init_persona()`` function will used the passed ``TokenSet`` instance instead of
    loading it from the cache and will write the tokens to the cache after validating them.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"

    token_set = TokenSet(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    assert not access_token_path.exists()
    assert not refresh_token_path.exists()

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    with plummet.frozen_time("2022-02-16 21:30:00"):
        persona = init_persona(dummy_context, token_set)

    assert persona.token_set.access_token == access_token
    assert persona.token_set.refresh_token == refresh_token
    assert persona.identity_data.client_id == "dummy-client"
    assert persona.identity_data.email == "good@email.com"

    assert access_token_path.exists()
    assert access_token_path.read_text() == access_token
    assert refresh_token_path.exists()


def test_init_persona__refreshes_access_token_if_it_is_expired(make_token, tmp_path, respx_mock, dummy_context, mocker):
    """
    Validate that the ``init_persona()`` function will refresh the access token if it is expired and, after
    validating it, save it to the cache.
    """
    access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-16 22:30:00",
    )
    access_token_path = tmp_path / "access.jwt"
    access_token_path.write_text(access_token)
    refresh_token = "dummy-refresh-token"
    refresh_token_path = tmp_path / "refresh.jwt"
    refresh_token_path.write_text(refresh_token)

    refreshed_access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-17 22:30:00",
    )

    respx_mock.post(f"{LOGIN_DOMAIN}/oauth/token").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(access_token=refreshed_access_token),
        ),
    )

    mocker.patch.object(settings, "JOBBERGATE_ACCESS_TOKEN_PATH", new=access_token_path)
    mocker.patch.object(settings, "JOBBERGATE_REFRESH_TOKEN_PATH", new=refresh_token_path)
    with plummet.frozen_time("2022-02-16 23:30:00"):
        persona = init_persona(dummy_context)

    assert persona.token_set.access_token == refreshed_access_token
    assert persona.token_set.refresh_token == refresh_token
    assert persona.identity_data.client_id == "dummy-client"
    assert persona.identity_data.email == "good@email.com"

    assert access_token_path.exists()
    assert access_token_path.read_text() == refreshed_access_token
    assert refresh_token_path.exists()
    assert refresh_token_path.read_text() == refresh_token


def test_refresh_access_token__success(make_token, respx_mock, dummy_context):
    """
    Validate that the ``refreshed_access_token()`` function uses a refresh token to retrieve a new access
    token from the ``oauth/token`` endpoint of the ``settings.OIDC_DOMAIN``.
    """
    access_token = "expired-access-token"
    refresh_token = "dummy-refresh-token"
    token_set = TokenSet(access_token=access_token, refresh_token=refresh_token)

    refreshed_access_token = make_token(
        azp="dummy-client",
        email="good@email.com",
        expires="2022-02-17 22:30:00",
    )

    respx_mock.post(f"{LOGIN_DOMAIN}/oauth/token").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(access_token=refreshed_access_token),
        ),
    )

    refresh_access_token(dummy_context, token_set)
    assert token_set.access_token == refreshed_access_token


def test_refresh_access_token__raises_abort_on_non_200_response(respx_mock, dummy_context):
    """
    Validate that the ``refreshed_access_token()`` function raises an abort if the response from the
    ``oauth/token`` endpoint of the ``settings.OIDC_DOMAIN`` is not a 200.
    """
    access_token = "expired-access-token"
    refresh_token = "dummy-refresh-token"
    token_set = TokenSet(access_token=access_token, refresh_token=refresh_token)

    respx_mock.post(f"{LOGIN_DOMAIN}/oauth/token").mock(
        return_value=httpx.Response(
            httpx.codes.BAD_REQUEST,
            json=dict(error_description="BOOM!"),
        ),
    )

    with pytest.raises(Abort, match="auth token could not be refreshed"):
        refresh_access_token(dummy_context, token_set)


def test_fetch_auth_tokens__success(respx_mock, dummy_context):
    """
    Validate that the ``fetch_auth_tokens()`` function can successfully retrieve auth tokens from the
    OIDC provider.
    """

    access_token = "dummy-access-token"
    refresh_token = "dummy-refresh-token"

    respx_mock.post(f"{LOGIN_DOMAIN}/auth/device").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                device_code="dummy-code",
                verification_uri_complete="https://dummy-uri.com",
                interval=1,
            ),
        ),
    )
    respx_mock.post(f"{LOGIN_DOMAIN}/token").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        ),
    )
    token_set = fetch_auth_tokens(dummy_context)
    assert token_set.access_token == access_token
    assert token_set.refresh_token == refresh_token


def test_fetch_auth_tokens__raises_Abort_when_it_times_out_waiting_for_the_user(respx_mock, dummy_context, mocker):
    """
    Validate that the ``fetch_auth_tokens()`` function will raise an Abort if the time runs out before a user
    completes the login process.
    """
    respx_mock.post(f"{LOGIN_DOMAIN}/auth/device").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                device_code="dummy-code",
                verification_uri_complete="https://dummy-uri.com",
                interval=0,
            ),
        ),
    )
    respx_mock.post(f"{LOGIN_DOMAIN}/token").mock(
        return_value=httpx.Response(httpx.codes.BAD_REQUEST, json=dict(error="authorization_pending")),
    )
    one_tick = Tick(counter=1, elapsed=pendulum.Duration(seconds=1), total_elapsed=pendulum.Duration(seconds=1))
    mocker.patch("jobbergate_cli.auth.TimeLoop", return_value=[one_tick])
    with pytest.raises(Abort, match="not completed in time"):
        fetch_auth_tokens(dummy_context)
