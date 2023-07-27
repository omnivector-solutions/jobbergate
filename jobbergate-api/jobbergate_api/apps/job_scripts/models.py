"""
Database model for the JobScript resource.
"""
from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.models import Base, CrudMixin, FileMixin
from jobbergate_api.safe_types import JobSubmission


class JobScript(CrudMixin, Base):
    """
    Job script table definition.

    Attributes:
        parent_template_id: The id of the parent template.

    See Mixin class definitions for other columns
    """

    parent_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_script_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    files: Mapped[list[JobScriptFile]] = relationship(
        "JobScriptFile",
        back_populates="parent",
        lazy="selectin",
        uselist=True,
        cascade="all, delete-orphan",
    )

    submissions: Mapped[list[JobSubmission]] = relationship(
        "JobSubmission",
        back_populates="job_script",
        lazy="selectin",
        uselist=True,
    )

    @classmethod
    def searchable_fields(cls):
        """
        Add parent_template_id as a searchable field.
        """
        return [cls.parent_template_id, *super().searchable_fields()]

    @classmethod
    def sortable_fields(cls):
        """
        Add parent_template_id as a sortable field.
        """
        return [cls.parent_template_id, *super().sortable_fields()]


class JobScriptFile(FileMixin, Base):
    """
    Job script files table definition.

    Attributes:
        parent_template_id: The id of the parent template.
        file_type: The type of the file.

    See Mixin class definitions for other columns
    """

    parent_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(JobScript.id, ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, native_enum=False), nullable=False)

    parent: Mapped["JobScript"] = relationship(
        "JobScript",
        back_populates="files",
        lazy="selectin",
    )
