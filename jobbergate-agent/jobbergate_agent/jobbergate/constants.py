from auto_name_enum import AutoNameEnum, auto


class FileType(AutoNameEnum):
    """File type enum."""

    ENTRYPOINT = auto()
    SUPPORT = auto()
