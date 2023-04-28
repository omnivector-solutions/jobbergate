"""
Database model for the JobScript resource.
"""
from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.models import Base, BaseFieldsMixin, ExtraFieldsMixin, Mapped, mapped_column


class JobScript(Base, BaseFieldsMixin, ExtraFieldsMixin):
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
    parent_template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_script_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    files: Mapped[list["JobScriptFile"]] = relationship("JobScriptFile", lazy="subquery")


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
