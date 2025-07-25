from enum import Enum


class JobSubmissionStatus(str, Enum):
    """
    Defines the set of possible statuses for a Job Submission.
    """

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    DONE = "DONE"
    ABORTED = "ABORTED"
    CANCELLED = "CANCELLED"
