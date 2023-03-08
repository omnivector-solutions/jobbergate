"""Constants to be shared by all models."""

from enum import Enum


class FileType(str, Enum):
    """File type enum."""

    ENTRYPOINT = "ENTRYPOINT"
    SUPPORT = "SUPPORT"
