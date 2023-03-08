"""Database models for the smart template resource."""
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.schema import Column

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.models import Base, BaseFieldsMixin


class SmartTemplate(Base, BaseFieldsMixin):
    """Smart template table definition."""

    __tablename__ = "smart_templates"

    id: int = Column(
        Integer,
        ForeignKey(JobScriptTemplate.id, ondelete="CASCADE"),
        primary_key=True,
    )
    identifier: str = Column(
        String,
        ForeignKey(JobScriptTemplate.identifier),
        unique=True,
    )
    runtime_config: dict[str, Any] = Column(
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    @property
    def file_key(self) -> str:
        return f"{self.__tablename__}/{self.id}/jobbergate.py"
