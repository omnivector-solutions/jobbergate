from enum import Enum


class FileType(str, Enum):
    """File type enum."""

    ENTRYPOINT = "ENTRYPOINT"
    SUPPORT = "SUPPORT"


APPLICATION_SCRIPT_FILE_NAME = "jobbergate.py"
