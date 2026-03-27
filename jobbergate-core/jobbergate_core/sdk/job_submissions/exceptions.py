"""Custom exceptions for job submissions module."""

from jobbergate_core.sdk.job_submissions.schemas import JobSubmissionDetailedView


class JobSubmissionError(Exception):
    """
    Base exception for errors related to job submissions.
    """

    pass


class JobSubmissionRejectedError(JobSubmissionError, ValueError):
    """
    Exception raised when a job submission is rejected.

    Includes the last retrieved submission data for consumer access.
    """

    def __init__(self, job_submission_id: int, submission: JobSubmissionDetailedView) -> None:
        """
        Initialize the exception.

        Args:
            job_submission_id: The ID of the rejected job submission.
            submission: The last retrieved submission data.
        """
        self.job_submission_id = job_submission_id
        self.submission = submission
        message = f"The job submission with ID {job_submission_id} was rejected and does not have a SLURM job ID."
        super().__init__(message)


class JobSubmissionTimeoutError(JobSubmissionError, TimeoutError):
    """
    Exception raised when a job submission SLURM ID is not set within timeout.

    Includes the last retrieved submission data for consumer access.
    """

    def __init__(self, job_submission_id: int, max_retries: int, submission: JobSubmissionDetailedView) -> None:
        """
        Initialize the exception.

        Args:
            job_submission_id: The ID of the job submission.
            max_retries: The maximum number of retry attempts.
            submission: The last retrieved submission data.
        """
        self.job_submission_id = job_submission_id
        self.max_retries = max_retries
        self.submission = submission
        message = (
            f"The SLURM job ID for submission {job_submission_id} was not set within {max_retries} retry attempts."
        )
        super().__init__(message)
