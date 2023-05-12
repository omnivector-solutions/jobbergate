"""Database models for the job_script_templates resource."""
from typing import Any, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.models import Base, BaseFieldsMixin, ExtraFieldsMixin, Mapped, mapped_column


class JobScriptTemplate(Base, BaseFieldsMixin, ExtraFieldsMixin):
    """
    Job script template table definition.

    Attributes:
        id: The id of the job script template.
        identifier: The identifier of the job script template.
        name: The name of the job script template.
        description: The description of the job script template.
        owner_email: The email of the owner of the job script template.
        template_vars: The template variables of the job script template.
        created_at: The date and time when the job script template was created.
        updated_at: The date and time when the job script template was updated.
    """

    __tablename__ = "job_script_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    template_vars: Mapped[dict[str, Any]] = mapped_column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    )

    template_files: Mapped[list["JobScriptTemplateFile"]] = relationship(
        "JobScriptTemplateFile", lazy="subquery"
    )
    workflow_file: Mapped["WorkflowFile"] = relationship("WorkflowFile", lazy="subquery")


class JobScriptTemplateFile(Base, BaseFieldsMixin):
    """Job script template files table definition."""

    __tablename__ = "job_script_template_files"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(JobScriptTemplate.id, ondelete="CASCADE"),
        primary_key=True,
    )
    filename: Mapped[str] = mapped_column(String, primary_key=True)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType), nullable=False)

    @hybrid_property
    def file_key(self) -> str:
        return f"{self.__tablename__}/{self.id}/{self.filename}"


class WorkflowFile(Base, BaseFieldsMixin):
    """
    Workflow file table definition.

    Attributes:
        id: The id of the workflow (foreign key from job-script-template).
        runtime_config: The runtime configuration of the workflow.
        created_at: The date and time when the workflow was created.
        updated_at: The date and time when the workflow was updated.
    """

    __tablename__ = "workflow_files"

    id: Mapped[int] = mapped_column(
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

    @property
    def file_key(self) -> str:
        """Return the file key for the workflow file."""
        return f"{self.__tablename__}/{self.id}/{WORKFLOW_FILE_NAME}"


job_script_templates_table = JobScriptTemplate.__table__
job_script_template_files_table = JobScriptTemplateFile.__table__
workflow_files_table = WorkflowFile.__table__
