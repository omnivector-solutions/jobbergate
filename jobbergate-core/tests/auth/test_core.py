"""
Test the utilities for handling auth in Jobbergate.
"""
from unittest import mock

import pytest
import requests

from jobbergate_core.auth import JobbergateAuth
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
    Return a dummy JobbergateAuth object.
    """
    return JobbergateAuth(
        cache_directory=tmp_path,
        login_domain=DUMMY_LOGIN_DOMAIN,
        login_audience=DUMMY_LOGIN_AUDIENCE,
        login_client_id=DUMMY_LOGIN_CLIENT_ID,
    )


def test_auth_base_case(tmp_path, dummy_jobbergate_auth):
    """
    Test that the JobbergateAuth class can be instantiated.
    """
    assert dummy_jobbergate_auth.cache_directory == tmp_path
    assert dummy_jobbergate_auth.login_domain == DUMMY_LOGIN_DOMAIN
    assert dummy_jobbergate_auth.login_audience == DUMMY_LOGIN_AUDIENCE
    assert dummy_jobbergate_auth.login_client_id == DUMMY_LOGIN_CLIENT_ID
    assert dummy_jobbergate_auth.tokens == {}


class TestJobbergateAuthCall:
    """
    Test the __call__ on JobbergateAuth class, used to authenticate the requests.
    """

    def test__success__insert_token_in_header(
        self,
        respx_mock,
        dummy_jobbergate_auth,
        valid_token,
    ):
        """
        Test that the JobbergateAuth class insert the token in the header.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = valid_token

        test_headers = {"test-header": "test-value", "foo": "bar"}
        expected_headers = {**test_headers, "Authorization": f"Bearer {valid_token.content}"}

        test_endpoint = "http://test.com"
        respx_mock.get(test_endpoint).mock()
        request = requests.Request(
            "GET",
            test_endpoint,
            auth=dummy_jobbergate_auth,
            headers=test_headers,
        )

        assert request.headers == test_headers
        with mock.patch.object(dummy_jobbergate_auth, "acquire_tokens") as mock_acquire_tokens:
            prepared_request = request.prepare()
            mock_acquire_tokens.assert_called_once()
        assert prepared_request.headers == expected_headers

    def test__fail__no_access_token(
        self,
        respx_mock,
        dummy_jobbergate_auth,
    ):
        """
        Test that the JobbergateAuth class fails if there is no access token.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = ""

        test_headers = {"test-header": "test-value", "foo": "bar"}

        test_endpoint = "http://test.com"
        respx_mock.get(test_endpoint).mock()
        request = requests.Request(
            "GET",
            test_endpoint,
            auth=dummy_jobbergate_auth,
            headers=test_headers,
        )

        assert request.headers == test_headers
        with mock.patch.object(dummy_jobbergate_auth, "acquire_tokens") as mock_acquire_tokens:
            with pytest.raises(AuthenticationError, match="Access token was not found"):
                request.prepare()
            mock_acquire_tokens.assert_called_once()
        assert request.headers == test_headers

    def test_get_validated_access_token__success(self, dummy_jobbergate_auth, valid_token):
        """
        Test that the get_validated_access_token function works as expected.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = valid_token

        assert dummy_jobbergate_auth._get_validated_access_token() == valid_token

    def test_get_validated_access_token__fail_token_not_found(self, dummy_jobbergate_auth):
        """
        Test that the get_validated_access_token fails if the token is not found.
        """
        with pytest.raises(AuthenticationError, match="Access token was not found"):
            dummy_jobbergate_auth._get_validated_access_token()

    def test_get_validated_access_token__fail_token_is_expired(
        self,
        dummy_jobbergate_auth,
        expired_token,
    ):
        """
        Test that the get_validated_access_token fails if the token is expired.
        """
        dummy_jobbergate_auth.tokens[TokenType.ACCESS] = expired_token
        with pytest.raises(AuthenticationError, match="Access token has expired"):
            dummy_jobbergate_auth._get_validated_access_token()


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
