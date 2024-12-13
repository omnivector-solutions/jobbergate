from typing import Literal

from auto_name_enum import AutoNameEnum, auto


class FileType(AutoNameEnum):
    """File type enum."""

    ENTRYPOINT = auto()
    SUPPORT = auto()


INFLUXDB_MEASUREMENT = Literal[
    "CPUFrequency",
    "CPUTime",
    "CPUUtilization",
    "GPUMemMB",
    "GPUUtilization",
    "Pages",
    "RSS",
    "ReadMB",
    "VMSize",
    "WriteMB",
]
