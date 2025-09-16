"""
Utilities for handling tokens on Jobbergate.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, TypedDict

import pendulum
from jose.jwt import decode
from loguru import logger

from jobbergate_core.auth.exceptions import TokenError


class TokenType(str, Enum):
    """
    The types of tokens available in the system are ``access`` and ``refresh``.
    """

    ACCESS = "access"
    REFRESH = "refresh"


class TokenData(TypedDict, total=False):
    """
    Expected data from the token to make type checking easier.
    """

    email: str
    azp: str
    exp: int
    iat: int
    organization: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Token:
    """
    Low-level class used to handle tokens.

    Arguments:
        cache_directory: The directory used for cache.
        label: The type of token.
        content: The content of the token (default is ``""``).

    Attributes:
        file_path: The path to the file associated with the token.
          It is computed  as ``<cache_directory>/<label>.token``.
        data: Metadata decoded from the token's content are available in this dictionary.
          Expiration date and permissions are some examples of data that can be found.
    """

    cache_directory: Path
    label: str
    content: str = ""
    file_path: Path = field(init=False, hash=False, repr=False)
    data: TokenData = field(
        default_factory=lambda: TokenData(),
        init=False,
        hash=False,
        repr=False,
    )

    def __post_init__(self):
        """
        Post init method.
        """
        TokenError.require_condition(isinstance(self.content, str), "Token content is not a string.")

        # There is one point to keep in mind when using frozen=True
        # see https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(
            self,
            "file_path",
            self.cache_directory / f"{self.label}.token",
        )
        if self.content:
            data = self._get_metadata()
            object.__setattr__(self, "data", data)

    def _get_metadata(self) -> TokenData:
        """
        Extract the data from the token.
        """
        with TokenError.handle_errors("Unable to extract data from the token"):
            data = decode(
                token=self.content,
                key="secret-will-be-ignored",
                options=dict(
                    verify_signature=False,
                    verify_aud=False,
                    verify_iat=False,
                    verify_exp=False,
                    verify_nbf=False,
                    verify_iss=False,
                    verify_sub=False,
                    verify_jti=False,
                    verify_at_hash=False,
                ),
            )

        return TokenData(**data)

    def load_from_cache(self) -> Token:
        """
        Load the token from the cache directory.

        Args:
            cache_directory: The path to the cache directory.
            label: The type of token.

        Returns:
            A new token with the content replaced.
        """
        file_path = self.cache_directory / f"{self.label}.token"
        logger.debug(f"Loading {self.label} token from {file_path.as_posix()}")

        TokenError.require_condition(file_path.exists(), "Token file was not found")

        with TokenError.handle_errors("Unknown error while loading the token"):
            content = file_path.read_text().strip()

        return self.replace(content=content)

    def save_to_cache(self) -> None:
        """
        Save the token to the cache file associated with it.

        Raises:
            TokenError: If the parent directory does not exist.
            TokenError: If there is an unknown error while saving the token.
        """
        if not self.content:
            return
        logger.debug(f"Saving {self.label} token to {self.file_path}")
        TokenError.require_condition(self.file_path.parent.exists(), "Parent directory does not exist")

        with TokenError.handle_errors("Unknown error while saving the token"):
            self.file_path.write_text(self.content.strip())
            self.file_path.chmod(0o600)

    def clear_cache(self) -> None:
        """
        Clear the token from cache by removing the file associated with it.
        """
        logger.debug(f"Clearing cached token from {self.file_path}")
        if self.file_path.exists():
            self.file_path.unlink()

    def is_expired(self) -> bool:
        """
        Check if the token is expired.

        Returns:
            True if the token is expired, False otherwise.

        Raises:
            TokenError: If the expiration date is not found.
        """
        TokenError.require_condition(
            "exp" in self.data, f"Failed checking {self.label} token since the expiration date was not found"
        )
        token_expiration = self.data["exp"]

        current_time_UTC = pendulum.now(tz="UTC").int_timestamp
        is_expired = token_expiration <= current_time_UTC
        logger.debug(f"{self.label.capitalize()} token is {'' if is_expired else 'NOT'} expired")

        return is_expired

    def is_valid(self) -> bool:
        """
        Verify if the token is valid, i.e., has content and is not expired.
        """
        return bool(self.content) and self.is_expired() is False

    def replace(self, **changes) -> Token:
        """
        Create a new instance of the token with the changes applied.

        Keyword Arguments:
            content: The content of the token.
            cache_directory: The directory containing the cache.
            label: The type of token.
        """
        return replace(self, **changes)

    @property
    def bearer_token(self) -> str:
        """
        Return the token with the ``Bearer`` prefix.
        """
        return f"Bearer {self.content}"
