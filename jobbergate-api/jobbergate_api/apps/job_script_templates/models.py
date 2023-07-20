"""Database models for the job_script_templates resource."""
from typing import Any, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column, relationship

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.models import Base, CrudMixin, FileMixin


class JobScriptTemplate(CrudMixin, Base):
    """
    Job script template table definition.

    Attributes:
        identifier: The identifier of the job script template.
        template_vars: The template variables of the job script template.

    See Mixin class definitions for other columns
    """

    identifier: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    template_vars: Mapped[dict[str, Any]] = mapped_column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    template_files: Mapped[list["JobScriptTemplateFile"]] = relationship(
        "JobScriptTemplateFile",
        back_populates="parent",
        lazy="selectin",
        uselist=True,
        cascade="all, delete-orphan",
    )
    workflow_files: Mapped[list["WorkflowFile"]] = relationship(
        "WorkflowFile",
        back_populates="parent",
        lazy="selectin",
        uselist=True,
        cascade="all, delete-orphan",
    )

    @classmethod
    def searchable_fields(cls):
        """
        Add identifier as a searchable field.
        """
        return [cls.identifier, *super().searchable_fields()]

    @classmethod
    def sortable_fields(cls):
        """
        Add identifier as a sortable field.
        """
        return [cls.identifier, *super().sortable_fields()]


class JobScriptTemplateFile(FileMixin, Base):
    """
    Job script template files table definition.

    Attributes:
        parent_id: A foreign key to the parent job script template row.
        file_type: The type of the file.

    See Mixin class definitions for other columns
    """

    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(JobScriptTemplate.id, ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, native_enum=False), nullable=False)

    parent: Mapped["JobScriptTemplate"] = relationship(
        "JobScriptTemplate",
        back_populates="template_files",
        lazy="selectin",
    )


class WorkflowFile(FileMixin, Base):
    """
    Workflow file table definition.

    Attributes:
        parent_id:      A foreign key to the parent job script template row.
        runtime_config: The runtime configuration of the workflow.

    See Mixin class definitions for other columns
    """

    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(JobScriptTemplate.id, ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    runtime_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    parent: Mapped["JobScriptTemplate"] = relationship(
        "JobScriptTemplate",
        back_populates="workflow_files",
        lazy="selectin",
    )
