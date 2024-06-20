from pathlib import Path
from typing import List, Optional

import pydantic
from pydantic import ConfigDict

from jobbergate_agent.jobbergate.constants import FileType


class JobScriptFile(pydantic.BaseModel, extra="ignore"):
    """Model for the job_script_files field of the JobScript resource."""

    parent_id: int
    filename: str
    file_type: FileType

    @property
    def path(self) -> str:
        return f"/jobbergate/job-scripts/{self.parent_id}/upload/{self.filename}"


class JobScript(pydantic.BaseModel, extra="ignore"):
    """Model to match database for the JobScript resource."""

    files: List[JobScriptFile] = pydantic.Field(default_factory=list)


class PendingJobSubmission(pydantic.BaseModel, extra="ignore"):
    """
    Specialized model for the cluster-agent to pull a pending job_submission along with
    data from its job_script and application sources.
    """

    id: int
    name: str
    owner_email: str
    execution_directory: Optional[Path] = None
    sbatch_arguments: List[str] = pydantic.Field(default_factory=list)
    job_script: JobScript


class ActiveJobSubmission(pydantic.BaseModel, extra="ignore"):
    """
    Specialized model for the cluster-agent to pull an active job_submission.
    """

    id: int
    slurm_job_id: int


class SlurmSubmitError(pydantic.BaseModel):
    """
    Specialized model for error content in a SlurmSubmitResponse.
    """

    error: Optional[str] = None
    error_code: Optional[int] = pydantic.Field(alias="errno")
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SlurmSubmitResponse(pydantic.BaseModel, extra="ignore"):
    """
    Specialized model for the cluster-agent to pull a pending job_submission along with
    data from its job_script and application sources.
    """

    errors: List[SlurmSubmitError] = []
    job_id: Optional[int] = None


class SlurmJobData(pydantic.BaseModel, extra="ignore"):
    """
    Specialized model for the cluster-agent to pull job state information from slurm and post the data as an update
    to the Jobbergate API.
    """

    job_id: Optional[int] = None
    job_state: Optional[str] = None
    job_info: Optional[str] = None
    state_reason: Optional[str] = None
