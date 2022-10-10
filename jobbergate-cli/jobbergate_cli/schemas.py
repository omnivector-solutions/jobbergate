"""
Provide Pydantic models for various data items.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pydantic


class TokenSet(pydantic.BaseModel, extra=pydantic.Extra.ignore):
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


class Persona(pydantic.BaseModel):
    """
    A model representing a pairing of a TokenSet and user email.
    This is a convenience to combine all of the identifying data and credentials for a given user.
    """

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    A model representing the data that is returned from the OIDC provider's device code endpoint.
    """

    device_code: str
    verification_uri_complete: str
    interval: int


class JobbergateContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """
    A data object describing context passed from the main entry point.
    """

    persona: Optional[Persona]
    full_output: bool = False
    raw_output: bool = False
    client: Optional[httpx.Client]


class JobbergateConfig(pydantic.BaseModel):
    """
    A data object describing the config values needed in the "jobbergate_config" section of the
    JobbergateApplicationConfig model.
    """

    template_files: Optional[List[Path]]
    default_template: Optional[str] = None
    output_directory: Optional[Path] = None
    supporting_files_output_name: Optional[Dict[str, Any]] = None
    supporting_files: Optional[List[Path]] = None

    # For some reason, we support the application_config being about to override the *required*
    # job_script_name parameter that is passed at job_script creation time.
    # TODO: Find if this functionality is every used, and, if not, remove it immediately.
    job_script_name: Optional[str] = None


class JobbergateApplicationConfig(pydantic.BaseModel):
    """
    A data object describing the config data needed to instantiate a JobbergateApplication class.
    """

    jobbergate_config: JobbergateConfig
    application_config: Dict[str, Any]


class ApplicationResponse(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Describes the format of data for applications retrieved from the Jobbergate API endpoints.
    """

    id: int
    application_name: str
    application_identifier: Optional[str] = None
    application_description: Optional[str] = None
    application_owner_email: str
    application_uploaded: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    application_config: Optional[str] = None
    application_source_file: Optional[str] = None
    application_templates: Optional[Dict[str, str]] = None


class JobScriptFiles(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Model containing job-script files.
    """

    main_file_path: Path
    files: Dict[str, str]


class JobScriptResponse(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Describes the format of data for job_scripts retrieved from the Jobbergate API endpoints.
    """

    id: int
    application_id: int
    job_script_name: str
    job_script_description: Optional[str] = None
    job_script_files: JobScriptFiles
    job_script_owner_email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobSubmissionResponse(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    Describes the format of data for job_submissions retrieved from the Jobbergate API endpoints.
    """

    id: int
    job_script_id: int
    cluster_name: Optional[str] = pydantic.Field(alias="client_id")
    slurm_job_id: Optional[int]
    execution_directory: Optional[Path]
    job_submission_name: str
    job_submission_description: Optional[str] = None
    job_submission_owner_email: str
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class JobScriptCreateRequestData(pydantic.BaseModel):
    """
    Describes the data that will be sent to the ``create`` endpoint of the Jobbergate API for job scripts.
    """

    application_id: int
    job_script_name: str
    job_script_description: Optional[str]
    param_dict: Optional[JobbergateApplicationConfig] = None
    sbatch_params: Optional[List[Any]] = None


class JobSubmissionCreateRequestData(pydantic.BaseModel):
    """
    Describes the data that will be sent to the ``create`` endpoint of the Jobbergate API for job submissions.
    """

    job_submission_name: str
    job_submission_description: Optional[str] = None
    job_script_id: int
    client_id: Optional[str] = pydantic.Field(None, alias="cluster_name")
    execution_directory: Optional[Path] = None


class Pagination(pydantic.BaseModel):
    """
    A model describing the structure of the pagination component of a ListResponseEnvelope.
    """

    total: int
    start: Optional[int]
    limit: Optional[int]


class ListResponseEnvelope(pydantic.BaseModel):
    """
    A model describing the structure of response envelopes from "list" endpoints.
    """

    results: List[Dict[str, Any]]
    pagination: Pagination


class ClusterCacheData(pydantic.BaseModel):
    """
    Describes the format of data stored in the clusters cache file.
    """

    updated_at: datetime
    client_ids: List[str]


class ForeignKeyError(pydantic.BaseModel):
    """
    A model describing the structure of a foreign-key constraint error on delete.
    """

    message: str
    table: str
    pk_id: int
