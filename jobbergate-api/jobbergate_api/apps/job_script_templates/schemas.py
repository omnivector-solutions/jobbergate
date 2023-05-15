from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


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
    filename: str
    file_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class WorkflowFileResponse(BaseModel):
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

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
