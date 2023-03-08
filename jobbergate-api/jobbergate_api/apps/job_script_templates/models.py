"""Database models for the job_script_templates resource."""
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.schema import Column

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.models import Base, BaseFieldsMixin, FileMixin, NameDescriptionEmailMixin


class JobScriptTemplate(Base, BaseFieldsMixin, NameDescriptionEmailMixin):
    """Job script template table definition."""

    __tablename__ = "job_script_templates"

    id: int = Column(Integer, primary_key=True)
    template_vars: dict[str, Any] = Column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )


class JobScriptTemplateFiles(Base, BaseFieldsMixin, FileMixin):
    """Job script template files table definition."""

    __tablename__ = "job_script_template_files"

    id: int = Column(
        Integer,
        ForeignKey(JobScriptTemplate.id, ondelete="CASCADE"),
        primary_key=True,
    )
    filename: str = Column(String, primary_key=True)
    file_type: str = Column(Enum(FileType), nullable=False)

    @property
    def file_key(self) -> str:
        return f"job_script_template_files/{self.id}/{self.filename}"
