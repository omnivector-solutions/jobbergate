"""Database models for the smart template resource."""
from typing import Any

from sqlalchemy import Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.schema import Column

from jobbergate_api.apps.models import Base, BaseFieldsMixin, NameDescriptionEmailMixin


class SmartTemplate(Base, BaseFieldsMixin, NameDescriptionEmailMixin):
    """Smart template table definition."""

    __tablename__ = "smart_templates"

    id: int = Column(Integer, primary_key=True)
    identifier: str = Column(String, unique=True, index=True)
    runtime_config: dict[str, Any] = Column(
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    @hybrid_property
    def file_key(self) -> str:
        return f"smart_templates/{self.id}/jobbergate.py"
