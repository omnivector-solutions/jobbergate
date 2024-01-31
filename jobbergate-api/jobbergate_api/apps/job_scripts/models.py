"""
Database model for the JobScript resource.
"""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate as JobScriptTemplateModel
from jobbergate_api.apps.models import Base, CrudMixin, FileMixin
from jobbergate_api.safe_types import JobScriptTemplate, JobSubmission


class JobScript(CrudMixin, Base):
    """
    Job script table definition.

    Notice all relationships are lazy="raise" to prevent n+1 implicit queries.
    This means that the relationships must be explicitly eager loaded using
    helper functions in the class.

    Attributes:
        parent_template_id: The id of the parent template.

    See Mixin class definitions for other columns.
    """

    parent_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_script_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    files: Mapped[list[JobScriptFile]] = relationship(
        "JobScriptFile",
        back_populates="parent",
        lazy="raise",
        uselist=True,
        cascade="all, delete-orphan",
    )

    template: Mapped[JobScriptTemplate] = relationship(
        "JobScriptTemplate",
        back_populates="scripts",
        lazy="raise",
    )
    submissions: Mapped[list[JobSubmission]] = relationship(
        "JobSubmission",
        back_populates="job_script",
        lazy="raise",
        uselist=True,
    )

    @classmethod
    def sortable_fields(cls):
        """
        Add parent_template_id as a sortable field.
        """
        return {cls.parent_template_id, *super().sortable_fields()}

    @classmethod
    def include_files(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load files.
        """
        return query.options(selectinload(cls.files))

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load parent data.
        """
        return query.options(selectinload(cls.template).defer(JobScriptTemplateModel.template_vars))


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
