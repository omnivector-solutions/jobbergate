"""
Provide schemas for the job script templates component.
"""

from typing import Any

from pydantic import BaseModel, NonNegativeInt
from jobbergate_core.sdk.constants import FileType
from jobbergate_core.sdk.schemas import PydanticDateTime, TableResource


class TemplateFileDetailedView(BaseModel):
    """Schema for the response to get a template file."""

    parent_id: NonNegativeInt
    filename: str
    file_type: FileType
    created_at: PydanticDateTime
    updated_at: PydanticDateTime


class WorkflowFileDetailedView(BaseModel):
    """Schema for the response to get a workflow file."""

    parent_id: NonNegativeInt
    filename: str
    runtime_config: dict[str, Any] | None = {}
    created_at: PydanticDateTime
    updated_at: PydanticDateTime


class JobTemplateListView(TableResource):
    """Schema for the response to get a list of entries."""

    identifier: str | None = None
    cloned_from_id: NonNegativeInt | None = None


class JobTemplateBaseDetailedView(JobTemplateListView):
    """
    Schema for the request to an entry.

    Notice the files are omitted.
    """

    template_vars: dict[str, Any] | None


class JobTemplateDetailedView(JobTemplateBaseDetailedView):
    """
    Schema for the request to an entry.

    Notice the files default to None, as they are not always requested, to differentiate between
    an empty list when they are requested, but no file is found.
    """

    template_files: list[TemplateFileDetailedView] | None
    workflow_files: list[WorkflowFileDetailedView] | None
