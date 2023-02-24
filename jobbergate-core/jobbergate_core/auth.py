"""
Utilities for handling auth in Jobbergate.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import buzz
import pendulum
from jose.jwt import decode
from loguru import logger


@dataclass
class Token:
    """
    Class for handling tokens.
    """

    content: Optional[str] = None
    cache_path: Optional[Path] = None
    label: Optional[str] = "unknown"
    data: Dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """
        Post init method.
        """
        if self.content:
            self._update_data()

    def _validate_cache_path(self):
        """
        Validate the cache path.
        """
        with buzz.check_expressions(
            f"Error while saving {self.label} token",
        ) as check:
            check(self.cache_path is not None, "No cache path specified")
            if self.cache_path is not None:
                check(
                    self.cache_path.parent.exists(),
                    f"Cache path {self.cache_path.parent.as_posix()} does not exist",
                )

    def save_to_cache(self):
        """
        Save the token to the cache.
        """
        self._validate_cache_path()
        logger.debug(f"Saving {self.label} token to {self.cache_path.as_posix()}")
        buzz.require_condition(self.content, "No token content specified")

        with buzz.handle_errors("Unknown error while saving the token"):
            self.cache_path.write_text(self.content.strip())
            self.cache_path.chmod(0o600)

    def load_from_cache(self):
        """
        Load the token from the cache.
        """
        self._validate_cache_path()
        logger.debug(f"Loading {self.label} token from {self.cache_path.as_posix()}")

        with buzz.handle_errors("Unknown error while loading the token"):
            self.content = self.cache_path.read_text().strip()

        self._update_data()

    def clear_cache(self):
        """
        Clear the cache.
        """
        logger.debug(f"Clearing cached {self.label} token")
        if self.cache_path is not None and self.cache_path.exists():
            self.cache_path.unlink()

    def _validate_content(self):
        """
        Validate token's content.
        """
        with buzz.check_expressions(
            f"Error while getting data from {self.label} token",
        ) as check:
            check(self.content is not None, "Token content is None")
            check(self.content != "", "Token content is empty")

    def _update_data(self):
        """
        Get the data from the token.
        """
        logger.debug(f"Getting data from {self.label} token")

        self._validate_content()

        with buzz.handle_errors("Unknown error while getting data from the token"):
            self.data = decode(
                self.content,
                None,
                options=dict(
                    verify_signature=False,
                    verify_aud=False,
                    verify_exp=False,
                ),
            )

    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        """
        logger.debug(f"Checking if {self.label} token has expired")
        token_expiration = self.data.get("exp")
        buzz.require_condition(
            token_expiration is not None,
            "The expiration date was not found",
        )

        current_time_UTC = pendulum.now().int_timestamp
        is_expired = token_expiration >= current_time_UTC
        logger.debug(f"    Token is expired: {is_expired}")

        return is_expired
