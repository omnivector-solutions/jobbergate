"""
Database model for the JobScript resource.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column, relationship
from sqlalchemy.sql import functions

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.models import Base, BaseFieldsMixin, Mapped, mapped_column


class JobScript(Base):
    """
    Job script table definition.

    Attributes:
        id: The id of the job script.
        name: The name of the job script.
        description: The description of the job script.
        owner_email: The email of the owner of the job script.
        parent_template_id: The id of the parent template.
        created_at: The date and time when the job script was created.
        updated_at: The date and time when the job script was updated.
    """

    __tablename__ = "job_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, default=None, nullable=True)
    owner_email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_script_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=functions.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=functions.now(),
        onupdate=functions.current_timestamp(),
    )

    files: Mapped[dict[str, "JobScriptFile"]] = relationship(
        "JobScriptFile",
        lazy="subquery",
        collection_class=attribute_keyed_dict("filename"),
        cascade="all, delete-orphan",
    )

    searchable_fields = [
        description,
        name,
        owner_email,
    ]
    sortable_fields = [
        id,
        name,
        owner_email,
        created_at,
        updated_at,
    ]


class JobScriptFile(Base, BaseFieldsMixin):
    """Job script files table definition."""

    __tablename__ = "job_script_files"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(JobScript.id, ondelete="CASCADE"),
        primary_key=True,
    )
    filename: Mapped[str] = mapped_column(String, primary_key=True)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType), nullable=False)

    @hybrid_property
    def file_key(self) -> str:
        """Return the file key."""
        return f"{self.__tablename__}/{self.id}/{self.filename}"


job_scripts_table = JobScript.__table__

searchable_fields = [
    job_scripts_table.c.name,
    job_scripts_table.c.description,
    job_scripts_table.c.owner_email,
]

sortable_fields = [
    job_scripts_table.c.id,
    job_scripts_table.c.name,
    job_scripts_table.c.owner_email,
    job_scripts_table.c.parent_template_id,
    job_scripts_table.c.created_at,
    job_scripts_table.c.updated_at,
]
