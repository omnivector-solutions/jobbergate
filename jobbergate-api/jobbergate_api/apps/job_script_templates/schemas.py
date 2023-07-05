import json
import urllib.parse
from datetime import datetime
from typing import Any, Optional

import pydantic
from pydantic import BaseModel, root_validator


class RunTimeConfig(BaseModel, extra=pydantic.Extra.allow):
    """Schema for the runtime config of a job template."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


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

    path: Optional[str]

    @root_validator
    def _compute_url(cls, values):
        values["path"] = "/jobbergate/job-script-templates/{}/upload/template/{}".format(
            values["id"],
            urllib.parse.quote(values["filename"], safe=""),
        )

        return values

    class Config:
        orm_mode = True


class WorkflowFileResponse(BaseModel):
    id: int
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    path: Optional[str]

    @root_validator
    def _compute_url(cls, values):
        values["path"] = f"/jobbergate/job-script-templates/{values['id']}/upload/workflow"

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

    template_files: Optional[dict[str, TemplateFileResponse]] = {}
    workflow_file: Optional[WorkflowFileResponse]

    class Config:
        orm_mode = True
