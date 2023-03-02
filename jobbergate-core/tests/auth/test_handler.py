"""
Test the utilities for handling auth in Jobbergate.
"""
from unittest import mock

import httpx
import pytest
import requests

from jobbergate_core.auth import JobbergateAuthHandler
from jobbergate_core.auth.exceptions import AuthenticationError
from jobbergate_core.auth.token import Token, TokenType


DUMMY_LOGIN_DOMAIN = "http://keycloak.local:8080/realms/jobbergate-local"
DUMMY_LOGIN_AUDIENCE = "https://local.omnivector.solutions"
DUMMY_LOGIN_CLIENT_ID = "cli"


@pytest.fixture
def valid_token(tmp_path, time_now, jwt_token):
    """
    Return a valid token.
    """

    return Token(
        content=jwt_token(exp=time_now.int_timestamp - 10),
        cache_directory=tmp_path,
        label=TokenType.ACCESS,
    )


@pytest.fixture
def expired_token(tmp_path, time_now, jwt_token):
    """
    Return an expired token.
    """
    return Token(
        content=jwt_token(exp=time_now.int_timestamp + 10),
        cache_directory=tmp_path,
        label=TokenType.ACCESS,
    )


@pytest.fixture
def dummy_jobbergate_auth(tmp_path):
    """
    Return a dummy JobbergateAuthHandler object.
    """
    return JobbergateAuthHandler(
        cache_directory=tmp_path,
        login_domain=DUMMY_LOGIN_DOMAIN,
        login_audience=DUMMY_LOGIN_AUDIENCE,
        login_client_id=DUMMY_LOGIN_CLIENT_ID,
    )


def test_auth_base_case(tmp_path, dummy_jobbergate_auth):
    """
    Test that the JobbergateAuthHandler class can be instantiated.
    """
    assert dummy_jobbergate_auth.cache_directory == tmp_path
    assert dummy_jobbergate_auth.login_domain == DUMMY_LOGIN_DOMAIN
    assert dummy_jobbergate_auth.login_audience == DUMMY_LOGIN_AUDIENCE
    assert dummy_jobbergate_auth.login_client_id == DUMMY_LOGIN_CLIENT_ID
    assert dummy_jobbergate_auth.tokens == {}


class TestJobbergateCheckCredentials:
    """
    Test the check_credentials method on JobbergateAuthHandler class.
    """

    def test_check_credentials__success(self, dummy_jobbergate_auth, valid_token):
        """
        Test that the function works as expected.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = valid_token

        assert dummy_jobbergate_auth.check_credentials(token_type=TokenType.ACCESS) == valid_token

    def test_check_credentials__fail_token_not_found(self, dummy_jobbergate_auth):
        """
        Test that get_credentials fails if the token is not found.
        """
        dummy_jobbergate_auth.tokens.clear()  # make sure there is no token

        with pytest.raises(AuthenticationError, match="access token was not found"):
            dummy_jobbergate_auth.check_credentials()

    def test_check_credentials__fail_token_is_expired(self, dummy_jobbergate_auth, expired_token):
        """
        Test that get_credentials fails if the token is expired.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = expired_token
        with pytest.raises(AuthenticationError, match="access token has expired"):
            dummy_jobbergate_auth.check_credentials(token_type=TokenType.ACCESS)


def test_insert_token_in_request_header(respx_mock, dummy_jobbergate_auth, valid_token):
    """
    Test that the JobbergateAuthHandler class inserts the token in the header (performed by __call__).
    """
    dummy_headers = {"test-header": "test-value", "foo": "bar"}
    expected_headers = {**dummy_headers, "Authorization": f"Bearer {valid_token.content}"}

    test_endpoint = "http://test.com"
    respx_mock.get(test_endpoint).mock()
    request = requests.Request("GET", test_endpoint, auth=dummy_jobbergate_auth, headers=dummy_headers)

    assert request.headers == dummy_headers

    with mock.patch.multiple(
        dummy_jobbergate_auth,
        acquire_tokens=mock.DEFAULT,
        check_credentials=lambda *args, **kwargs: valid_token,
    ) as mocked_jobbergate_auth:
        prepared_request = request.prepare()

        for mocked in mocked_jobbergate_auth.values():
            mocked.call_count = 1

    assert prepared_request.headers == expected_headers


@pytest.mark.parametrize(
    "available_tokens, expected_call_count",
    [
        (
            {},
            {"login": 1},
        ),  # no token available, login is needed
        (
            {TokenType.ACCESS: True},
            {},
        ),  # access token is available, no further action is needed
        (
            {TokenType.REFRESH: True},
            {"refresh_tokens": 1},
        ),  # just refresh token is available, refresh can get a new access token
        (
            {TokenType.ACCESS: False},
            {"login": 1},
        ),  # just expired access token is available, login is needed
        (
            {TokenType.REFRESH: False},
            {"login": 1},
        ),  # just expired refresh token is available, login is needed
        (
            {TokenType.ACCESS: False, TokenType.REFRESH: True},
            {"refresh_tokens": 1},
        ),  # access is expired, but refresh is not, we can get a new access token
        (
            {TokenType.ACCESS: True, TokenType.REFRESH: False},
            {},
        ),  # refresh is expired, but access is still good, no further action is needed
        (
            {TokenType.ACCESS: True, TokenType.REFRESH: True},
            {},
        ),  # both tokens are good to go, no further action is needed
        (
            {TokenType.ACCESS: False, TokenType.REFRESH: False},
            {"login": 1},
        ),  # both tokens are expired, login is needed
    ],
)
def test_acquire_tokens(
    available_tokens,
    expected_call_count,
    dummy_jobbergate_auth,
    valid_token,
    expired_token,
):
    """
    Test that the acquire_tokens function works as expected.

    The acquire_tokens function should:
        * Load the tokens from the cache directory
        * If the access token is unavailable or expired, refresh both tokens
          using the refresh token.
        * If the refresh token is unavailable or expired, login to fetch both tokens

    This test covers all possible scenarios, making sure that the correct functions are
    called according to the tokens available in the class.
    """
    # Map True and False to valid and expired tokens, respectively. A workaround to allow
    # the use of fixtures here, since pytest does not allow fixtures in parametrize
    dummy_jobbergate_auth.tokens = {
        key: valid_token if value else expired_token for key, value in available_tokens.items()
    }

    expected_call_count["load_from_cache"] = 1  # always called once

    with mock.patch.multiple(
        dummy_jobbergate_auth,
        load_from_cache=mock.DEFAULT,
        refresh_tokens=mock.DEFAULT,
        login=mock.DEFAULT,
    ) as mocked_jobbergate_auth:
        dummy_jobbergate_auth.acquire_tokens()

        for key in mocked_jobbergate_auth.keys():
            assert mocked_jobbergate_auth[key].call_count == expected_call_count.get(key, 0)


class TestJobbergateAuthHandlerLoadFromCache:
    """
    Test the load_from_cache method on JobbergateAuthHandler class.
    """

    def test_no_tokens_found(self, dummy_jobbergate_auth):
        """
        Test that the function works as expected.

        If no tokens are found in cache, the tokens dictionary should stay empty.
        """
        assert dummy_jobbergate_auth.tokens == {}

        dummy_jobbergate_auth.load_from_cache()

        assert dummy_jobbergate_auth.tokens == {}

    def test_tokens_found__skip_loaded(self, dummy_jobbergate_auth, valid_token, expired_token):
        """
        Test that the function works as expected.

        If a token is already loaded in the class, it should not be overwritten.
        """
        cached_tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: expired_token.replace(label=TokenType.REFRESH),
        }
        for token in cached_tokens.values():
            token.save_to_cache()

        internal_tokens = {
            TokenType.ACCESS: valid_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

        dummy_jobbergate_auth.tokens = internal_tokens.copy()

        dummy_jobbergate_auth.load_from_cache(skip_loaded=True)

        assert dummy_jobbergate_auth.tokens == internal_tokens
        assert dummy_jobbergate_auth.tokens != cached_tokens

    def test_tokens_found__not_skip_loaded(self, dummy_jobbergate_auth, valid_token, expired_token):
        """
        Test that the function works as expected.

        If a token is already loaded in the class, it should be replaced.
        """
        cached_tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: expired_token.replace(label=TokenType.REFRESH),
        }
        for token in cached_tokens.values():
            token.save_to_cache()

        internal_tokens = {
            TokenType.ACCESS: valid_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

        dummy_jobbergate_auth.tokens = internal_tokens.copy()

        dummy_jobbergate_auth.load_from_cache(skip_loaded=False)

        assert dummy_jobbergate_auth.tokens != internal_tokens
        assert dummy_jobbergate_auth.tokens == cached_tokens


def test_save_to_cache(dummy_jobbergate_auth, valid_token):
    """
    Test that the save_to_cache function works as expected.

    The save_to_cache function should:
        * Create the cache directory if it does not exist
        * Save the tokens to the cache directory
    """
    new_cache_directory = dummy_jobbergate_auth.cache_directory / "new_cache"

    dummy_jobbergate_auth.cache_directory = new_cache_directory
    dummy_jobbergate_auth.tokens = {
        TokenType.ACCESS: valid_token.replace(
            label=TokenType.ACCESS,
            cache_directory=new_cache_directory,
        ),
        TokenType.REFRESH: valid_token.replace(
            label=TokenType.REFRESH,
            cache_directory=new_cache_directory,
        ),
    }

    assert new_cache_directory.exists() is False

    dummy_jobbergate_auth.save_to_cache()

    assert new_cache_directory.exists() is True
    for token in dummy_jobbergate_auth.tokens.values():
        assert token.file_path.read_text() == token.content


class TestJobbergateAuthHandlerRefreshTokens:
    """
    Test the refresh_tokens method on JobbergateAuthHandler class.
    """

    def test_refresh_tokens__success(
        self,
        respx_mock,
        jwt_token,
        dummy_jobbergate_auth,
        expired_token,
        valid_token,
    ):
        """
        Test that the function works as expected.
        """
        dummy_jobbergate_auth.tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

        refreshed_access_token_content = jwt_token(custom_data="refreshed_access_token")
        refreshed_refresh_token_content = jwt_token(custom_data="refreshed_refresh_token")
        expected_refreshed_tokens = {
            TokenType.ACCESS: valid_token.replace(
                label=TokenType.ACCESS,
                content=refreshed_access_token_content,
            ),
            TokenType.REFRESH: valid_token.replace(
                label=TokenType.REFRESH,
                content=refreshed_refresh_token_content,
            ),
        }

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dict(
                    access_token=refreshed_access_token_content,
                    refresh_token=refreshed_refresh_token_content,
                ),
            ),
        )

        dummy_jobbergate_auth.refresh_tokens()

        assert dummy_jobbergate_auth.tokens == expected_refreshed_tokens

    def test_refresh_tokens__failure_by_missing_data(
        self,
        respx_mock,
        jwt_token,
        dummy_jobbergate_auth,
        expired_token,
        valid_token,
    ):
        """
        Test that the function raises an exception if the response is missing data.
        """
        dummy_jobbergate_auth.tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

        refreshed_access_token_content = jwt_token(custom_data="refreshed_access_token")

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dict(access_token=refreshed_access_token_content),
            ),  # note that the refresh token is missing
        )
        with pytest.raises(
            AuthenticationError,
            match="Not all tokens were included in the response",
        ):
            dummy_jobbergate_auth.refresh_tokens()

    def test_refresh_tokens__request_failure(
        self,
        respx_mock,
        dummy_jobbergate_auth,
        expired_token,
        valid_token,
    ):
        """
        Test that the function raises an exception if the tokens are not refreshed.
        """
        dummy_jobbergate_auth.tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(httpx.codes.BAD_REQUEST),
        )

        with pytest.raises(
            AuthenticationError,
            match="Unexpected error while refreshing the tokens",
        ):
            dummy_jobbergate_auth.refresh_tokens()


def test_logout_success(dummy_jobbergate_auth, valid_token):
    """
    Test that the logout function works as expected.
    """
    dummy_jobbergate_auth.tokens = {
        TokenType.ACCESS: valid_token.replace(label=TokenType.ACCESS),
        TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
    }

    token_path = [t.file_path for t in dummy_jobbergate_auth.tokens.values()]

    dummy_jobbergate_auth.save_to_cache()

    assert all([path.is_file() is True for path in token_path])

    dummy_jobbergate_auth.logout()

    assert all([path.is_file() is False for path in token_path])


class TestJobbergateAuthHandlerLogin:
    """
    Test the login method on JobbergateAuthHandler class.
    """

    def test_login__success(self, respx_mock, dummy_jobbergate_auth, valid_token):
        """
        Test that the function works as expected.
        """

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/auth/device"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dict(
                    device_code="dummy-code",
                    verification_uri_complete="https://dummy-uri.com",
                    interval=1,
                    expires_in=0.5,
                ),
            ),
        )

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dict(
                    access_token=valid_token.content,
                    refresh_token=valid_token.content,
                ),
            ),
        )

        dummy_jobbergate_auth.login()

        assert dummy_jobbergate_auth.tokens == {
            TokenType.ACCESS: valid_token.replace(label=TokenType.ACCESS),
            TokenType.REFRESH: valid_token.replace(label=TokenType.REFRESH),
        }

    def test_login__raises_timeout(self, respx_mock, dummy_jobbergate_auth):
        """
        Test that the function raises an exception if the process times out.
        """
        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/auth/device"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dict(
                    device_code="dummy-code",
                    verification_uri_complete="https://dummy-uri.com",
                    interval=1,
                    expires_in=1e-8,  # very small value to force timeout
                ),
            ),
        )

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(
                httpx.codes.BAD_REQUEST,
            ),
        )

        with pytest.raises(AuthenticationError, match="Login expired, please try again"):
            dummy_jobbergate_auth.login()
