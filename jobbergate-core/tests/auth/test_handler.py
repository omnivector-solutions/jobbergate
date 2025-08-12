"""
Test the utilities for handling auth in Jobbergate.
"""

from dataclasses import replace
from unittest import mock

import httpx
import pendulum
import pytest
import requests

from jobbergate_core.auth import JobbergateAuthHandler
from jobbergate_core.auth.exceptions import AuthenticationError
from jobbergate_core.auth.token import TokenType


DUMMY_LOGIN_DOMAIN = "http://keycloak.local:8080/realms/jobbergate-local"
DUMMY_LOGIN_CLIENT_ID = "cli"


@pytest.fixture
def dummy_jobbergate_auth(tmp_path):
    """
    Return a dummy JobbergateAuthHandler object.
    """
    return JobbergateAuthHandler(
        cache_directory=tmp_path,
        login_domain=DUMMY_LOGIN_DOMAIN,
        login_client_id=DUMMY_LOGIN_CLIENT_ID,
    )


def test_auth_base_case(tmp_path, dummy_jobbergate_auth):
    """
    Test that the JobbergateAuthHandler class can be instantiated.
    """
    assert dummy_jobbergate_auth.cache_directory == tmp_path
    assert dummy_jobbergate_auth.login_domain == DUMMY_LOGIN_DOMAIN
    assert dummy_jobbergate_auth.login_client_id == DUMMY_LOGIN_CLIENT_ID

    assert dummy_jobbergate_auth._access_token.content == ""
    assert dummy_jobbergate_auth._access_token.cache_directory == tmp_path
    assert dummy_jobbergate_auth._access_token.label == TokenType.ACCESS

    assert dummy_jobbergate_auth._refresh_token.content == ""
    assert dummy_jobbergate_auth._refresh_token.cache_directory == tmp_path
    assert dummy_jobbergate_auth._refresh_token.label == TokenType.REFRESH


def test_insert_token_in_request_header(respx_mock, dummy_jobbergate_auth, valid_token):
    """
    Test that the JobbergateAuthHandler class inserts the token in the header (performed by __call__).
    """
    dummy_headers = {"test-header": "test-value", "foo": "bar"}
    expected_headers = {**dummy_headers, "Authorization": valid_token.bearer_token}

    test_endpoint = "http://test.com"
    respx_mock.get(test_endpoint).mock()
    request = requests.Request("GET", test_endpoint, auth=dummy_jobbergate_auth, headers=dummy_headers)

    assert request.headers == dummy_headers

    with mock.patch.object(
        dummy_jobbergate_auth,
        attribute="acquire_access",
        new=lambda *args, **kwargs: valid_token.bearer_token,
    ):
        prepared_request = request.prepare()

    assert prepared_request.headers == expected_headers


@pytest.mark.parametrize("procedure", (None, "load_from_cache", "refresh_tokens", "login"))
def test_acquire_access(procedure, dummy_jobbergate_auth, valid_token):
    """
    Test that the acquire_tokens method works as expected.

    The acquire_access method should try in this order until a valid access token is found:
        * Get the access token stored in the instance
        * Load the tokens from the cache directory
        * Refresh both tokens using the refresh token.
        * Login to fetch both tokens

    This test covers all possible scenarios, making sure that the correct functions are
    called according to the tokens available in the class.
    """
    expected_order_of_procedures = ("load_from_cache", "refresh_tokens", "login")

    def inject_valid_access_token(*args, **kwargs):
        dummy_jobbergate_auth._access_token = valid_token

    mock_params = {key: mock.DEFAULT for key in expected_order_of_procedures}
    if procedure is None:
        dummy_jobbergate_auth._access_token = valid_token
    else:
        mock_params[procedure] = inject_valid_access_token

    with mock.patch.multiple(dummy_jobbergate_auth, **mock_params) as mocked_jobbergate_auth:
        dummy_jobbergate_auth.acquire_access()

    actual_call_counter = {key: mocked.call_count for key, mocked in mocked_jobbergate_auth.items()}
    expected_call_counter = {e: 0 for e in expected_order_of_procedures}
    if procedure is not None:
        actual_call_counter[procedure] = 1
        for e in expected_order_of_procedures:
            expected_call_counter[e] = 1
            if e == procedure:
                break

    assert actual_call_counter == expected_call_counter


class TestJobbergateAuthHandlerLoadFromCache:
    """
    Test the load_from_cache method on JobbergateAuthHandler class.
    """

    def test_no_tokens_found(self, dummy_jobbergate_auth):
        """
        Test that the function works as expected.

        If no tokens are found in cache, the tokens dictionary should stay empty.
        """
        with pytest.raises(AuthenticationError, match="Token file was not found"):
            dummy_jobbergate_auth.load_from_cache()

    def test_tokens_found__replace_loaded(self, dummy_jobbergate_auth, valid_token, expired_token):
        """
        Test that the function works as expected.

        If a token is already loaded in the class, it should be replaced.
        """
        cached_tokens = {
            TokenType.ACCESS: expired_token.replace(label=TokenType.ACCESS.value),
            TokenType.REFRESH: expired_token.replace(label=TokenType.REFRESH.value),
        }
        for token in cached_tokens.values():
            token.save_to_cache()

        original_content = valid_token.content
        expected_content = expired_token.content

        dummy_jobbergate_auth.access_token = original_content
        dummy_jobbergate_auth.refresh_token = original_content

        dummy_jobbergate_auth.load_from_cache()

        assert dummy_jobbergate_auth._access_token.content == expected_content
        assert dummy_jobbergate_auth._refresh_token.content == expected_content


def test_save_to_cache(dummy_jobbergate_auth, valid_token):
    """
    Test that the save_to_cache function works as expected.

    The save_to_cache function should:
        * Create the cache directory if it does not exist
        * Save the tokens to the cache directory
    """
    new_cache_directory = dummy_jobbergate_auth.cache_directory / "new_cache"

    dummy_jobbergate_auth.cache_directory = new_cache_directory

    access_token = dummy_jobbergate_auth._access_token.replace(
        content=valid_token.content, cache_directory=new_cache_directory
    )
    dummy_jobbergate_auth._access_token = access_token
    refresh_token = dummy_jobbergate_auth._refresh_token.replace(
        content=valid_token.content, cache_directory=new_cache_directory
    )
    dummy_jobbergate_auth._refresh_token = refresh_token

    assert new_cache_directory.exists() is False

    dummy_jobbergate_auth.save_to_cache()

    assert new_cache_directory.exists() is True
    assert access_token.file_path.read_text() == access_token.content
    assert refresh_token.file_path.read_text() == refresh_token.content


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
        dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(
            content=expired_token.content,
        )
        dummy_jobbergate_auth._refresh_token = dummy_jobbergate_auth._refresh_token.replace(
            content=valid_token.content,
        )

        refreshed_access_token_content = jwt_token(custom_data="refreshed_access_token")
        refreshed_refresh_token_content = jwt_token(custom_data="refreshed_refresh_token")

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

        assert dummy_jobbergate_auth._access_token.content == refreshed_access_token_content
        assert dummy_jobbergate_auth._refresh_token.content == refreshed_refresh_token_content

    def test_refresh_tokens__failure_no_refresh_token(self, dummy_jobbergate_auth):
        """
        Test that the function raises an exception if there is no refresh token.
        """
        assert dummy_jobbergate_auth._refresh_token.content == ""
        with pytest.raises(
            AuthenticationError, match="Session can no be refreshed since the refresh token is unavailable"
        ):
            dummy_jobbergate_auth.refresh_tokens()

    def test_refresh_tokens__failure_expired_refresh_token(self, dummy_jobbergate_auth, expired_token):
        """
        Test that the function raises an exception if the refresh token is expired.
        """
        dummy_jobbergate_auth._refresh_token = dummy_jobbergate_auth._refresh_token.replace(
            content=expired_token.content,
        )
        with pytest.raises(AuthenticationError, match="Session can no be refreshed since the refresh token is expired"):
            dummy_jobbergate_auth.refresh_tokens()

    def test_refresh_tokens__request_failure(self, respx_mock, dummy_jobbergate_auth, valid_token):
        """
        Test that the function raises an exception if the tokens are not refreshed.
        """
        dummy_jobbergate_auth._refresh_token = dummy_jobbergate_auth._refresh_token.replace(
            content=valid_token.content,
        )

        endpoint = f"{dummy_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        respx_mock.post(endpoint).mock(
            return_value=httpx.Response(httpx.codes.BAD_REQUEST),
        )

        with pytest.raises(AuthenticationError):
            dummy_jobbergate_auth.refresh_tokens()


def test_logout_success(dummy_jobbergate_auth, valid_token):
    """
    Test that the logout function works as expected.
    """
    dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(
        content=valid_token.content,
    )
    dummy_jobbergate_auth._refresh_token = dummy_jobbergate_auth._refresh_token.replace(
        content=valid_token.content,
    )

    access_token_path = dummy_jobbergate_auth._access_token.file_path
    refresh_token_path = dummy_jobbergate_auth._refresh_token.file_path

    dummy_jobbergate_auth.save_to_cache()

    assert access_token_path.exists() is True
    assert refresh_token_path.exists() is True

    dummy_jobbergate_auth.logout()

    assert dummy_jobbergate_auth._access_token.content == ""
    assert dummy_jobbergate_auth._refresh_token.content == ""

    assert access_token_path.exists() is False
    assert refresh_token_path.exists() is False


class TestJobbergateAuthHandlerLogin:
    """
    Test the login method on JobbergateAuthHandler class.
    """

    def test_login__success(self, respx_mock, dummy_jobbergate_auth, valid_token):
        """
        Test that the function works as expected.
        """
        assert dummy_jobbergate_auth._access_token.content == ""
        assert dummy_jobbergate_auth._refresh_token.content == ""

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

        assert dummy_jobbergate_auth._access_token.content == valid_token.content
        assert dummy_jobbergate_auth._refresh_token.content == valid_token.content

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

        with pytest.raises(AuthenticationError, match="Login process was not completed in time"):
            dummy_jobbergate_auth.login()


class TestJobbergateAuthHandlerFromSecret:
    """
    Test the from_secret method on JobbergateAuthHandler class.
    """

    def test_secret__success(self, respx_mock, dummy_jobbergate_auth, valid_token):
        """
        Test that the function works as expected.
        """
        assert dummy_jobbergate_auth._access_token.content == ""

        secret_jobbergate_auth = replace(dummy_jobbergate_auth, login_client_secret="dummy-secret")

        endpoint = f"{secret_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        mocked = respx_mock.post(endpoint).mock(
            return_value=httpx.Response(httpx.codes.OK, json=dict(access_token=valid_token.content)),
        )

        secret_jobbergate_auth.get_access_from_secret()

        assert secret_jobbergate_auth._access_token.content == valid_token.content

        assert mocked.called

    def test_secret__bad_request(self, respx_mock, dummy_jobbergate_auth):
        """
        Test that the function works as expected.
        """

        secret_jobbergate_auth = replace(dummy_jobbergate_auth, login_client_secret="dummy-secret")

        endpoint = f"{secret_jobbergate_auth.login_domain}/protocol/openid-connect/token"
        mocked = respx_mock.post(endpoint).mock(return_value=httpx.Response(httpx.codes.BAD_REQUEST))

        with pytest.raises(AuthenticationError, match="Failed to get access token from client secret"):
            secret_jobbergate_auth.get_access_from_secret()

        assert dummy_jobbergate_auth._access_token.content == ""

        assert mocked.called


class TestJobbergateAuthHandlerGetIdentityData:
    """
    Test the get_identity_data method on JobbergateAuthHandler class.
    """

    @pytest.mark.parametrize(
        "org_field",
        [
            {"some-name": {"id": "some-id"}}, # New Keycloak json structure - PENG-3064
            {"some-id": {"name": "some-name"}}, # Legacy Keycloak json structure for backward compatibility
        ],
    )
    def test_get_identity_data__success(self, org_field, dummy_jobbergate_auth, jwt_token):
        """
        Test that the function works as expected.
        """

        access_token = jwt_token(
            azp="dummy-client",
            email="good@email.com",
            organization=org_field,
            exp=pendulum.tomorrow().int_timestamp,
        )
        dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(content=access_token)

        identity_data = dummy_jobbergate_auth.get_identity_data()

        assert identity_data.email == "good@email.com"
        assert identity_data.client_id == "dummy-client"
        assert identity_data.organization_id == "some-id"

    def test_get_identity_data__fails_no_email(self, dummy_jobbergate_auth, jwt_token):
        """
        Test that the function raises an exception if the email is missing.
        """

        access_token = jwt_token(
            azp="dummy-client",
            exp=pendulum.tomorrow().int_timestamp,
        )
        dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(content=access_token)

        with pytest.raises(AuthenticationError, match="Could not retrieve user email from token"):
            dummy_jobbergate_auth.get_identity_data()

    def test_get_identity_data__fails_no_client_id(self, dummy_jobbergate_auth, jwt_token):
        """
        Test that the function raises an exception if the client_id is missing.
        """

        access_token = jwt_token(
            email="good@email.com",
            exp=pendulum.tomorrow().int_timestamp,
        )
        dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(content=access_token)

        with pytest.raises(AuthenticationError, match="Could not retrieve client_id from token"):
            dummy_jobbergate_auth.get_identity_data()

    def test_get_identify_data__fails_more_than_one_organization(self, dummy_jobbergate_auth, jwt_token):
        """
        Test that the function raises an exception if there is more than one organization.
        """

        access_token = jwt_token(
            azp="dummy-client",
            email="good@email.com",
            organization={"some-id": "some-name", "other-id": "other-name"},
            exp=pendulum.tomorrow().int_timestamp,
        )
        dummy_jobbergate_auth._access_token = dummy_jobbergate_auth._access_token.replace(content=access_token)

        with pytest.raises(
            AuthenticationError,
            match="More than one organization id found in token payload",
        ):
            dummy_jobbergate_auth.get_identity_data()
