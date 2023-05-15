import urllib.parse
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, root_validator


class JobTemplateCreateRequest(BaseModel):
    """Schema for the request to create a job template."""

    name: str
    identifier: Optional[str]
    description: Optional[str]
    template_vars: Optional[dict[str, Any]]

    class Config:
        orm_mode = True


class JobTemplateUpdateRequest(BaseModel):
    """Schema for the request to update a job template."""

    name: Optional[str]
    identifier: Optional[str]
    description: Optional[str]
    template_vars: Optional[dict[str, Any]]

    class Config:
        orm_mode = True


class TemplateFileResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    url: Optional[str]

    @root_validator
    def _compute_url(cls, values):
        values["url"] = "jobbergate/job-script-templates/{}/upload/template/{}".format(
            values["id"],
            urllib.parse.quote(values["filename"], safe=""),
        )

        return values

    class Config:
        orm_mode = True


class WorkflowFileResponse(BaseModel):
    id: int
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

    url: Optional[str]

    @root_validator
    def _compute_url(cls, values):
        values["url"] = f"/jobbergate/job-script-templates/{values['id']}/upload/workflow"

        return values

    class Config:
        orm_mode = True


class JobTemplateResponse(BaseModel):
    """Schema for the request to create a job template."""

    id: int
    name: str
    owner_email: str
    created_at: datetime
    updated_at: datetime
    identifier: Optional[str]
    description: Optional[str]
    template_vars: Optional[dict[str, Any]] = {}

    template_files: list[TemplateFileResponse] = []
    workflow_file: Optional[WorkflowFileResponse]

    class Config:
        orm_mode = True
