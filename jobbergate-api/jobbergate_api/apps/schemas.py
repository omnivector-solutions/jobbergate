"""Define app-wide, reusable pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TableResource(BaseModel):
    """
    Describes a base for table models that include basic, common info.
    """

    id: int
    name: str
    owner_email: str
    created_at: datetime
    updated_at: datetime
    description: str | None
