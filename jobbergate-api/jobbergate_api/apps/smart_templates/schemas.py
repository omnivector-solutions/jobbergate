from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SmartTemplateCreateRequest(BaseModel):
    """Schema for the request to create a smart template."""

    id: int
    runtime_config: Optional[dict[str, Any]]

    class Config:
        orm_mode = True


class SmartTemplateUpdateRequest(BaseModel):
    """Schema for the request to update a smart template."""

    runtime_config: Optional[dict[str, Any]]

    class Config:
        orm_mode = True


class SmartTemplateResponse(BaseModel):
    """Schema for the request to create a smart template."""

    id: int
    name: str
    owner_email: str
    created_at: datetime
    updated_at: datetime
    identifier: Optional[str]
    description: Optional[str]
    runtime_config: Optional[dict[str, Any]] = {}

    class Config:
        orm_mode = True
