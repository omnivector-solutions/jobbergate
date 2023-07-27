"""
Provide schemas for the job script templates component.
"""

import json
from datetime import datetime
from typing import Any, Optional

import pydantic
from pydantic import BaseModel

from jobbergate_api.apps.schemas import TableResource


class RunTimeConfig(BaseModel, extra=pydantic.Extra.allow):
    """Schema for the runtime config of a job template."""

    @classmethod
    def __get_validators__(cls):
        """
        Get the validators.
        """
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        """
        Validate the produced json.
        """
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
    """Schema for the response to get a template file."""

    parent_id: int
    filename: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class WorkflowFileResponse(BaseModel):
    """Schema for the response to get a workflow file."""

    parent_id: int
    filename: str
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class JobTemplateResponse(TableResource):
    """Schema for the request to create a job template."""

    identifier: Optional[str]
    template_vars: Optional[dict[str, Any]] = {}

    template_files: list[TemplateFileResponse] = []
    workflow_files: list[WorkflowFileResponse] = []

    class Config:
        orm_mode = True
