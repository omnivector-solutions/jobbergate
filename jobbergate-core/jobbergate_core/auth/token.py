from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict

import pendulum
from jose.jwt import decode
from loguru import logger

from .exceptions import TokenError


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

    @property
    def expiration_date(self) -> str:
        """
        Get the expiration date of the token.
        """
        return str(pendulum.from_timestamp(self.data["exp"]))

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
