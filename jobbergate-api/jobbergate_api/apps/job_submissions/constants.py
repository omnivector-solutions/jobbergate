"""
Describe constants for the job_submissions module.
"""


from enum import Enum


class JobSubmissionStatus(str, Enum):
    """
    Defines the set of possible statuses for a Job Submission.
    """

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"

    @classmethod
    def pretty_list(cls):
        """
        Return a comma-separated list of possible statuses.
        """
        return ", ".join(str(e) for e in cls)
