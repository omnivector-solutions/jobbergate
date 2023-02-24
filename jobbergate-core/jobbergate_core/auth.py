"""
Utilities for handling auth in Jobbergate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import buzz
import httpx
import pendulum
from jose.jwt import decode
from loguru import logger


class AuthenticationError(buzz.Buzz):
    """
    Exception for errors related to authentication.
    """

    pass


class TokenError(AuthenticationError):
    """
    Exception for errors related to tokens.
    """

    pass


class TokenType(str, Enum):
    """
    Types of tokens.
    """

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class Token:
    """
    Class for handling tokens.
    """

    content: str
    cache_directory: Path
    label: TokenType
    file_path: Path = field(init=False, hash=False, repr=False)
    data: Dict[str, Any] = field(
        default_factory=dict,
        init=False,
        hash=False,
        repr=False,
    )

    def __post_init__(self):
        """
        Post init method.
        """
        TokenError.require_condition(bool(self.content), "Token content is empty")

        # There is one point to keep in mind when using frozen=True
        # see https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(
            self,
            "file_path",
            self.cache_directory / f"{self.label}.token",
        )
        data = self._get_metadata()
        object.__setattr__(self, "data", data)

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Extract the data from the token.
        """
        logger.debug(f"Getting data from {self.label} token")

        with TokenError.handle_errors("Unable to extract data from the token"):
            data = decode(
                token=self.content,
                key="",
                options=dict(
                    verify_signature=False,
                    verify_aud=False,
                    verify_exp=False,
                ),
            )

        return data

    @classmethod
    def load_from_cache(cls, cache_directory: Path, label: TokenType) -> Token:
        """
        Alternative initialization method that loads the token from the cache.
        """
        file_path = cache_directory / f"{label}.token"
        logger.debug(f"Loading token from {file_path.as_posix()}")

        TokenError.require_condition(file_path.exists(), "Token file was not found")

        with TokenError.handle_errors("Unknown error while loading the token"):
            content = file_path.read_text().strip()

        return cls(content=content, cache_directory=cache_directory, label=label)

    def save_to_cache(self):
        """
        Save the token to the cache.
        """
        logger.debug(f"Saving token to {self.file_path}")
        TokenError.require_condition(
            self.file_path.parent.exists(),
            "Parent directory does not exist",
        )

        with TokenError.handle_errors("Unknown error while saving the token"):
            self.file_path.write_text(self.content.strip())
            self.file_path.chmod(0o600)

    def clear_cache(self):
        """
        Clear the cache.
        """
        logger.debug(f"Clearing cached token from {self.file_path}")
        if self.file_path.exists():
            self.file_path.unlink()

    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        """
        logger.debug(f"Checking if {self.label} token has expired")
        token_expiration = self.data.get("exp", 0)
        TokenError.require_condition(token_expiration > 0, "The expiration date was not found")

        current_time_UTC = pendulum.now().int_timestamp
        is_expired = token_expiration >= current_time_UTC
        logger.debug(f"    Token is expired: {is_expired}")

        return is_expired

    def replace(self, **changes) -> Token:
        """
        Create a new instance of the token with the changes applied.
        """
        return replace(self, **changes)


@dataclass
class JobbergateAuth:
    """
    Class for handling authentication in Jobbergate.
    """

    cache_path: Path
    login_domain: str
    login_audience: str
    login_client_id: str
    access_token: Token
    refresh_token: Token
    token_list: List = field(init=False, repr=False)

    def __post_init__(self):
        """
        Post init method.
        """
        self.token_list = [self.access_token, self.refresh_token]

    def __call__(self, request):
        """
        Authenticate the request.
        """
        logger.debug("Authenticating request")
        request.headers["Authorization"] = f"Bearer {self.access_token.content}"
        return request

    @classmethod
    def load_from_cache(cls, cache_path: Path, **kwargs) -> JobbergateAuth:
        """
        Alternative initialization method that loads the tokens from the cache.
        """
        logger.debug(f"Loading tokens from {cache_path.as_posix()}")

        access_token = Token.load_from_cache(
            cache_path=cache_path / "access.token",
            label="access",
        )
        refresh_token = Token.load_from_cache(
            cache_path=cache_path / "refresh.token",
            label="refresh",
        )

        return cls(
            cache_path=cache_path,
            access_token=access_token,
            refresh_token=refresh_token,
            **kwargs,
        )

    def save_to_cache(self):
        """
        Save the tokens to the cache.
        """
        for token in self.token_list:
            token.save_to_cache()

    def login(self):
        """
        Login to Jobbergate.
        """
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
                response.raise_for_status()  # Will throw an exception if response isn't in 200s
                response_data = response.json()
                return (
                    response_data["access_token"],
                    response_data["refresh_token"],
                )
            except Exception:
                pass

    def refresh_tokens(self):
        """
        Refresh the tokens.
        """
        with AuthenticationError.handle_errors(
            "Unexpected error while refreshing the tokens",
        ):
            response = httpx.post(
                f"{self.login_domain}/protocol/openid-connect/token",
                data=dict(
                    client_id=self.login_client_id,
                    audience=self.login_audience,
                    grant_type="refresh_token",
                    refresh_token=self.refresh_token.content,
                ),
            )
            response.raise_for_status()

        refreshed_data = response.json()

        self.access_token = self.access_token.replace(
            content=refreshed_data.get("access_token"),
        )
        self.refresh_token = self.refresh_token.replace(
            content=refreshed_data.get("refresh_token"),
        )
