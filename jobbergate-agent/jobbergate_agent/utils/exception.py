"""Core module for exception related operations"""

from buzz import Buzz


class JobbergateAgentError(Buzz):
    """Raise exception when execution command returns an error"""


class ProcessExecutionError(JobbergateAgentError):
    """Raise exception when execution command returns an error"""


class AuthTokenError(JobbergateAgentError):
    """Raise exception when there are connection issues with the backend"""


class SbatchError(JobbergateAgentError):
    """Raise exception when sbatch raises any error"""


class JobbergateApiError(JobbergateAgentError):
    """Raise exception when communication with Jobbergate API fails"""


class JobSubmissionError(JobbergateAgentError):
    """Raise exception when a job cannot be submitted raises any error"""


class SlurmParameterParserError(JobbergateAgentError):
    """Raise exception when Slurm mapper or SBATCH parser face any error"""
