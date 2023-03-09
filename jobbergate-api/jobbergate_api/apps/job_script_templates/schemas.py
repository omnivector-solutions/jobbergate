from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class JobTemplateCreateRequest(BaseModel):
    """Schema for the request to create a job template."""

    name: str
    identifier: Optional[str]
    description: Optional[str]
    template_vars: Optional[dict[str, Any]]


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

    class Config:
        orm_mode = True
