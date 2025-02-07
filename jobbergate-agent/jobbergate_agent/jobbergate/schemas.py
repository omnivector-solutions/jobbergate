from pathlib import Path
from typing import List, Optional, TypedDict, TypeAlias

import pydantic
from pydantic import ConfigDict

from jobbergate_agent.jobbergate.constants import FileType, INFLUXDB_MEASUREMENT


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


class InfluxDBMeasurementDict(TypedDict):
    """
    Map each entry in the list returned by `InfluxDBClient(...).get_list_measurements(...)`.
    """

    name: INFLUXDB_MEASUREMENT


class InfluxDBPointDict(TypedDict):
    """
    Map each entry in the generator returned by InfluxDBClient(...).query(...).get_points().
    """

    time: int
    host: str
    job: str
    step: str
    task: str
    value: float
    measurement: INFLUXDB_MEASUREMENT


class JobSubmissionMetricsMaxTime(pydantic.BaseModel):
    """
    Model for the max_times field of the JobSubmissionMetricsMaxResponse.
    """

    max_time: int
    node_host: str
    step: int
    task: int


class JobSubmissionMetricsMaxResponse(pydantic.BaseModel):
    """
    Model for the response of the `/jobbergate/job-submissions/agent/metrics/{job_submission_id}` endpoint.
    """

    job_submission_id: int
    max_times: list[JobSubmissionMetricsMaxTime]


"""
Type alias for job metric structure. It matches the following sequence of data
(time, host, step, task, CPUFrequency, CPUTime, CPUUtilization, GPUMemMB,
GPUUtilization, Pages, RSS, VMSize, ReadMB, WriteMB)
"""
JobMetricData: TypeAlias = list[
    tuple[int, str, str, str, float, float, float, float, float, float, float, float, float, float]
]
