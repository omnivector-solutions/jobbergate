"""
Utilities for handling auth in Jobbergate.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

import httpx
from loguru import logger

from .exceptions import AuthenticationError, TokenError
from .token import Token, TokenType


@dataclass
class JobbergateAuth:
    """
    Class for handling authentication in Jobbergate.

    Arguments:
        cache_directory (Path): Directory to be used for the caching tokens.
        login_domain (str): Domain used for the login.
        login_audience (str): Audience of the login.
        login_client_id (str): Client ID used for login.
        tokens (Dict[TokenType, Token]): Dictionary holding the tokens needed for authentication.

    Examples:
        >>> from pathlib import Path
        >>> import requests
        >>> from jobbergate_core import JobbergateAuth
        >>> jobbergate_auth = JobbergateAuth(
        ...     cache_directory=Path("."),
        ...     login_domain="http://keycloak.local:8080/realms/jobbergate-local",
        ...     login_audience="https://local.omnivector.solutions",
        ...     login_client_id="cli",
        ... )
        >>> jobbergate_base_url = "http://localhost:8000/jobbergate"
        >>> jobbergate_auth.acquire_tokens()
        Login Here: http://keycloak.local:8080/realms/jobbergate-local/device?user_code=LMVJ-XOLG
        >>> response = requests.get(f"{jobbergate_base_url}/applications", auth=jobbergate_auth)
        >>> response.raise_for_status()
        >>> print(f"response = {response.json()}")
    """

    cache_directory: Path
    login_domain: str
    login_audience: str
    login_client_id: str
    tokens: Dict[TokenType, Token] = field(default_factory=dict)

    def __call__(self, request):
        """
        Authenticate the request.
        """
        logger.debug("Authenticating request")

        self.acquire_tokens()

        access_token = self.tokens.get(TokenType.ACCESS, "")
        AuthenticationError.require_condition(access_token, "Access token was not found")

        request.headers["Authorization"] = f"Bearer {access_token.content}"
        return request

    def acquire_tokens(self):
        """
        Acquire the tokens.
        """
        logger.debug("Acquiring tokens")
        self.load_from_cache(skip_loaded=True)
        if TokenType.ACCESS in self.tokens and not self.tokens[TokenType.ACCESS].is_expired():
            return
        elif TokenType.REFRESH in self.tokens and not self.tokens[TokenType.REFRESH].is_expired():
            self.refresh_tokens()
            return
        self.login()

    def load_from_cache(self, skip_loaded: bool = True):
        """
        Load the tokens from the cache.
        """
        logger.debug("Loading tokens from cache directory: {}", self.cache_directory.as_posix())

        for t in TokenType:
            if t in self.tokens and skip_loaded:
                continue
            try:
                new_token = Token.load_from_cache(self.cache_directory, label=t)
            except TokenError:
                logger.debug(f"    {t}.token was not found")
                continue
            self.tokens[t] = new_token

    def save_to_cache(self):
        """
        Save the tokens to the cache.
        """
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        for token in self.tokens.values():
            token.save_to_cache()

    def login(self):
        """
        Login to Jobbergate.
        """
        logger.debug("Preparing to login to Jobbergate")
        response = httpx.post(
            f"{self.login_domain}/protocol/openid-connect/auth/device",
            data=dict(
                client_id=self.login_client_id,
                grant_type="client_credentials",
                audience=self.login_audience,
            ),
        )
        device_code_data = response.json()
        verification_url = device_code_data["verification_uri_complete"]
        wait_interval = device_code_data["interval"]
        device_code = device_code_data["device_code"]

        print(f"Login Here: {verification_url}")
        while True:
            time.sleep(wait_interval)
            response = httpx.post(
                f"{self.login_domain}/protocol/openid-connect/token",
                data=dict(
                    grant_type="urn:ietf:params:oauth:grant-type:device_code",
                    device_code=device_code,
                    client_id=self.login_client_id,
                ),
            )
            try:
                response.raise_for_status()
                break
            except httpx.HTTPStatusError:
                continue

        self._process_tokens_from_response(response)

    def refresh_tokens(self):
        """
        Refresh the tokens.
        """
        logger.debug("Preparing to refresh the tokens")
        with AuthenticationError.handle_errors(
            "Unexpected error while refreshing the tokens",
        ):
            response = httpx.post(
                f"{self.login_domain}/protocol/openid-connect/token",
                data=dict(
                    client_id=self.login_client_id,
                    audience=self.login_audience,
                    grant_type="refresh_token",
                    refresh_token=self.tokens[TokenType.REFRESH].content,
                ),
            )
            response.raise_for_status()

        self._process_tokens_from_response(response)

    def _process_tokens_from_response(self, response):
        response_data = response.json()

        tokens_content = {t: response_data.get(f"{t}_token") for t in TokenType}
        AuthenticationError.require_condition(
            all(tokens_content.values()), "Not all tokens were included in the response"
        )
        self._update_tokens(tokens_content)
        self.save_to_cache()

    def _update_tokens(self, tokens_content: Dict[TokenType, str]):
        """
        Update the tokens with the new content.
        """

        for token_type, new_content in tokens_content.items():
            self.tokens[token_type] = Token(
                content=new_content,
                cache_directory=self.cache_directory,
                label=token_type,
            )
