from typing import Literal

from auto_name_enum import AutoNameEnum, auto


class FileType(AutoNameEnum):
    """File type enum."""

    ENTRYPOINT = auto()
    SUPPORT = auto()


class JobSubmissionStatus(AutoNameEnum):
    """
    Defines the set of possible statuses for a Job Submission.

    Notice only the statuses that are relevant to the cluster-agent are defined here.
    """

    CANCELLED = auto()


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
