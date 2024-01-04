from collections import defaultdict
from enum import Enum
from typing import DefaultDict


class FileType(str, Enum):
    """File type enum."""

    ENTRYPOINT = "ENTRYPOINT"
    SUPPORT = "SUPPORT"


class JobSubmissionStatus(str, Enum):
    """
    Enumeration of possible job_submission statuses.
    """

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


status_map: DefaultDict[str, JobSubmissionStatus] = defaultdict(
    lambda: JobSubmissionStatus.SUBMITTED,
    COMPLETED=JobSubmissionStatus.COMPLETED,
    FAILED=JobSubmissionStatus.FAILED,
    CANCELLED=JobSubmissionStatus.CANCELLED,
)
