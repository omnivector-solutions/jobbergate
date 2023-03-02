"""
Utilities for handling tokens on Jobbergate.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict

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


@dataclass(frozen=True)
class Token:
    """
    Low-level class used to handling tokens.

    Arguments:
        content (str): The content of the token.
        cache_directory (pathlib.Path): The directory used for cache.
        label (TokenType): The type of token.

    Attributes:
        file_path (pathlib.Path): The path to the file associated with the token.
          It is computed  as ``<cache_directory>/<label>.token``.
        data (dict[str, typing.Any]): Metadata decoded from the token's content
          are available in this dictionary. Expiration date and permissions are
          some examples of data that can be found.
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

        Args:
            cache_directory (Path): The path to the cache directory.
            label (TokenType): The type of token.

        Returns:
            Token: The loaded Token.
        """
        file_path = cache_directory / f"{label}.token"
        logger.debug(f"Loading token from {file_path.as_posix()}")

        TokenError.require_condition(file_path.exists(), "Token file was not found")

        with TokenError.handle_errors("Unknown error while loading the token"):
            content = file_path.read_text().strip()

        return cls(content=content, cache_directory=cache_directory, label=label)

    def save_to_cache(self) -> None:
        """
        Save the token to the cache file associated with it.

        Raises:
            TokenError: If the parent directory does not exist.
            TokenError: If there is an unknown error while saving the token.
        """
        logger.debug(f"Saving token to {self.file_path}")
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
            bool: True if the token is expired, False otherwise.

        Raises:
            TokenError: If the expiration date is not found.
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

        Keyword Arguments:
            content (str): The content of the token.
            cache_directory (Path): The directory containing the cache.
            label (TokenType): The type of token.
        """
        return replace(self, **changes)
