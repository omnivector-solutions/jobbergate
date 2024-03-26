from pathlib import Path
from typing import List, Optional

import pydantic

from jobbergate_agent.jobbergate.constants import FileType


class JobScriptFile(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """Model for the job_script_files field of the JobScript resource."""

    parent_id: int
    filename: str
    file_type: FileType

    @property
    def path(self) -> str:
        return f"/jobbergate/job-scripts/{self.parent_id}/upload/{self.filename}"


class JobScript(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """Model to match database for the JobScript resource."""

    files: List[JobScriptFile] = pydantic.Field(default_factory=list)


class PendingJobSubmission(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Specialized model for the cluster-agent to pull a pending job_submission along with
    data from its job_script and application sources.
    """

    id: int
    name: str
    owner_email: str
    execution_directory: Optional[Path]
    sbatch_arguments: List[str] = pydantic.Field(default_factory=list)
    job_script: JobScript


class ActiveJobSubmission(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Specialized model for the cluster-agent to pull an active job_submission.
    """

    id: int
    slurm_job_id: int


class SlurmJobParams(pydantic.BaseModel):
    """
    Specialized model for describing job submission parameters for Slurm REST API.
    """

    name: str
    get_user_environment: int = 1
    standard_error: Optional[Path]
    standard_output: Optional[Path]
    current_working_directory: Optional[Path]

    class Config:
        extra = "allow"


class SlurmJobSubmission(pydantic.BaseModel):
    """
    Specialized model for describing a request to submit a job to Slurm REST API.
    """

    script: str
    job: SlurmJobParams


class SlurmSubmitError(pydantic.BaseModel):
    """
    Specialized model for error content in a SlurmSubmitResponse.
    """

    error: Optional[str]
    error_code: Optional[int] = pydantic.Field(alias="errno")

    class Config:
        allow_population_by_field_name = True
        extra = pydantic.Extra.ignore


class SlurmSubmitResponse(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Specialized model for the cluster-agent to pull a pending job_submission along with
    data from its job_script and application sources.
    """

    errors: List[SlurmSubmitError] = []
    job_id: Optional[int]


class SlurmJobData(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Specialized model for the cluster-agent to pull job state information from slurm and post the data as an update
    to the Jobbergate API.
    """

    job_id: Optional[int]
    job_state: Optional[str]
    job_info: Optional[str]
    state_reason: Optional[str]
