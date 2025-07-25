"""
Provide Pydantic models for various data items.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar

import httpx
import pydantic
import pydantic.generics
from jobbergate_core.auth.handler import JobbergateAuthHandler
from jobbergate_core.sdk import Apps

from jobbergate_cli.constants import FileType


class TokenSet(pydantic.BaseModel, extra="ignore"):
    """
    A model representing a pairing of access and refresh tokens
    """

    access_token: str
    refresh_token: Optional[str] = None


class IdentityData(pydantic.BaseModel):
    """
    A model representing the identifying data for a user from an auth token.
    """

    email: str
    client_id: str
    organization_id: Optional[str] = None


class Persona(pydantic.BaseModel):
    """
    A model representing a pairing of a TokenSet and user email.
    This is a convenience to combine all of the identifying data and credentials for a given user.
    """

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(pydantic.BaseModel, extra="ignore"):
    """
    A model representing the data that is returned from the OIDC provider's device code endpoint.
    """

    device_code: str
    verification_uri_complete: str
    interval: int


class ContextProtocol(Protocol):
    """
    A protocol describing context passed from the main entry point.

    It aims to help static type checkers at the same time that prevents
    circular import issues on the actual implementation.
    """

    raw_output: bool
    full_output: bool

    @property
    def client(self) -> httpx.Client: ...

    @property
    def authentication_handler(self) -> JobbergateAuthHandler: ...

    @property
    def sdk(self) -> Apps: ...


class JobbergateConfig(pydantic.BaseModel, extra="allow"):
    """
    A data object describing the config values needed in the "jobbergate_config" section of the
    JobbergateApplicationConfig model.
    """

    template_files: Optional[List[Path]] = None
    default_template: Optional[str] = None
    supporting_files_output_name: Optional[Dict[str, List[str]]] = None
    supporting_files: Optional[List[str]] = None

    @pydantic.model_validator(mode="before")
    def compute_extra_settings(cls, values):
        """
        Compute missing values and extra operations to enhance the user experience and backward compatibility.
        """
        if values.get("supporting_files_output_name"):
            for k, v in values["supporting_files_output_name"].items():
                if isinstance(v, str):
                    values["supporting_files_output_name"][k] = [v]

        return values


class JobbergateApplicationConfig(pydantic.BaseModel):
    """
    A data object describing the config data needed to instantiate a JobbergateApplication class.
    """

    application_config: Dict[str, Any]
    jobbergate_config: JobbergateConfig


class TemplateFileResponse(pydantic.BaseModel, extra="ignore"):
    parent_id: int
    filename: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    @property
    def path(self) -> str:
        return f"/jobbergate/job-script-templates/{self.parent_id}/upload/template/{self.filename}"


class WorkflowFileResponse(pydantic.BaseModel, extra="ignore"):
    parent_id: int
    filename: str
    runtime_config: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    @property
    def path(self) -> str:
        return f"/jobbergate/job-script-templates/{self.parent_id}/upload/workflow"


class ApplicationResponse(pydantic.BaseModel, extra="ignore"):
    """
    Describes the format of data for applications retrieved from the Jobbergate API endpoints.
    """

    application_id: int = pydantic.Field(alias="id")
    name: str
    identifier: Optional[str] = None
    owner_email: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    template_vars: Dict[str, Any] = {}
    is_archived: Optional[bool] = None
    cloned_from_id: Optional[int] = None

    template_files: List[TemplateFileResponse] = []
    workflow_files: List[WorkflowFileResponse] = []


class LocalTemplateFile(pydantic.BaseModel, extra="ignore"):
    """
    Template file retrieved from a local folder.
    """

    filename: str
    path: Path
    file_type: FileType


class LocalWorkflowFile(pydantic.BaseModel, extra="ignore"):
    """
    Workflow file retrived from a local folder.
    """

    filename: str
    path: Path
    runtime_config: Dict[str, Any] = {}


class LocalApplication(pydantic.BaseModel, extra="ignore"):
    """
    Application retrieved from a local folder.
    """

    template_vars: Dict[str, Any] = {}

    template_files: List[LocalTemplateFile] = []
    workflow_files: List[LocalWorkflowFile] = []


class JobScriptFile(pydantic.BaseModel, extra="ignore"):
    """
    Model containing job-script files.
    """

    parent_id: int
    filename: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    @property
    def path(self) -> str:
        return f"/jobbergate/job-scripts/{self.parent_id}/upload/{self.filename}"


class JobScriptResponse(pydantic.BaseModel):
    """
    Describes the format of data for job_scripts retrieved from the Jobbergate API endpoints.
    """

    job_script_id: int = pydantic.Field(alias="id")
    name: str
    application_id: Optional[int] = pydantic.Field(None, alias="parent_template_id")
    description: Optional[str] = None
    owner_email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_archived: Optional[bool] = None
    cloned_from_id: Optional[int] = None

    files: List[JobScriptFile] = []

    @pydantic.field_validator("files", mode="before")
    @classmethod
    def null_files(cls, value):
        """
        Remap a `None` value in files to an empty list.
        """
        if value is None:
            return []
        return value

    model_config = pydantic.ConfigDict(populate_by_name=True, extra="ignore")


class JobSubmissionResponse(pydantic.BaseModel, extra="ignore"):
    """
    Describes the format of data for job_submissions retrieved from the Jobbergate API endpoints.
    """

    job_submission_id: int = pydantic.Field(alias="id")
    name: str
    slurm_job_id: Optional[int] = None
    slurm_job_state: Optional[str] = None
    slurm_job_info: Optional[str] = None
    job_script_id: Optional[int] = None
    cluster_name: Optional[str] = pydantic.Field(default=None, alias="client_id")
    description: Optional[str] = None
    execution_directory: Optional[Path] = None
    owner_email: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_archived: Optional[bool] = None
    report_message: Optional[str] = None
    sbatch_arguments: Optional[list[str]] = None
    cloned_from_id: Optional[int] = None


class JobScriptCreateRequest(pydantic.BaseModel):
    """
    Request model for creating JobScript instances.
    """

    name: str
    description: Optional[str] = None


class RenderFromTemplateRequest(pydantic.BaseModel):
    """Request model for creating a JobScript entry from a template."""

    template_output_name_mapping: Dict[str, str]
    sbatch_params: Optional[List[str]] = None
    param_dict: Dict[str, Any]


class JobScriptRenderRequestData(pydantic.BaseModel):
    """
    Describes the data that will be sent to the ``create`` endpoint of the Jobbergate API for job scripts.
    """

    create_request: JobScriptCreateRequest
    render_request: RenderFromTemplateRequest


class JobSubmissionCreateRequestData(pydantic.BaseModel):
    """
    Describes the data that will be sent to the ``create`` endpoint of the Jobbergate API for job submissions.
    """

    name: str
    description: Optional[str] = None
    job_script_id: int
    slurm_job_id: Optional[int] = None
    client_id: Optional[str] = pydantic.Field(None, alias="cluster_name")
    execution_directory: Optional[Path] = None
    sbatch_arguments: Optional[list[str]] = None


EnvelopeT = TypeVar("EnvelopeT")


class ListResponseEnvelope(pydantic.BaseModel, Generic[EnvelopeT]):
    """
    A model describing the structure of response envelopes from "list" endpoints.
    """

    items: List[EnvelopeT]
    total: int
    page: int
    size: int
    pages: int


class ClusterCacheData(pydantic.BaseModel):
    """
    Describes the format of data stored in the clusters cache file.
    """

    updated_at: datetime
    client_ids: List[str]
