import httpx
import pytest
import respx

from jobbergate_agent.clients.cluster_api import Token, TokenError, TokenType, acquire_token
from jobbergate_agent.settings import SETTINGS


def test_acquire_token__gets_a_token_from_the_cache(mock_cluster_api_cache_dir, token_content):
    """
    Verifies that the token is retrieved from the cache if it is found there.
    """
    mock_cluster_api_cache_dir.mkdir(parents=True)

    token = Token(cache_directory=mock_cluster_api_cache_dir, label=TokenType.ACCESS)
    token_path = token.file_path

    token_path.write_text(token_content)

    retrieved_token = acquire_token(token)
    assert retrieved_token.content == token_content

    assert retrieved_token.is_valid() is True


def test_acquire_token__gets_a_token_if_one_is_not_in_the_cache(
    mock_cluster_api_cache_dir,
    tweak_settings,
    token_content,
):
    """
    Verifies that a token is pulled from OIDC if it is not found in the cache.
    Also checks to make sure the token is cached.
    """
    mock_cluster_api_cache_dir.mkdir(parents=True)
    token = Token(cache_directory=mock_cluster_api_cache_dir, label=TokenType.ACCESS)

    token_path = token.file_path
    assert not token_path.exists()

    with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token").mock(
            return_value=httpx.Response(status_code=200, json={"access_token": token_content})
        )
        with tweak_settings(OIDC_CLIENT_ID="dummy", OIDC_CLIENT_SECRET="dummy"):
            retrieved_token = acquire_token(token)

    assert retrieved_token.content == token_content
    assert token_path.read_text() == token_content

    assert retrieved_token.is_valid() is True


def test_acquire_token__fails_when_content_is_invalid(
    mock_cluster_api_cache_dir,
    tweak_settings,
):
    """
    Verifies that a token is pulled from OIDC if it is not found in the cache.
    Also checks to make sure the token is cached.
    """
    mock_cluster_api_cache_dir.mkdir(parents=True)
    token = Token(cache_directory=mock_cluster_api_cache_dir, label=TokenType.ACCESS)

    token_content = "invalid-token-content"

    with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token").mock(
            return_value=httpx.Response(status_code=200, json={"access_token": token_content})
        )
        with tweak_settings(OIDC_CLIENT_ID="dummy", OIDC_CLIENT_SECRET="dummy"):
            with pytest.raises(TokenError):
                acquire_token(token)
