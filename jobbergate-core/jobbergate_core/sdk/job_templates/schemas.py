"""
Provide schemas for the job script templates component.
"""

import json
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class RunTimeConfig(BaseModel):
    """
    Schema for the runtime config of a job template.

    Notice this includes user supplied variables, so it has no predefined field.
    It also loads the contend directly from the json at the request payload.
    """

    @model_validator(mode="before")
    @classmethod
    def coerce_string_to_dict(cls, data):
        """
        Get the validators.
        """
        if isinstance(data, str):
            return json.loads(data)
        else:
            return data

    model_config = ConfigDict(extra="allow")


class JobTemplateCreateRequest(BaseModel):
    """Schema for the request to create a job template."""

    name: str
    identifier: str | None = None
    description: str | None = None
    template_vars: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def not_empty_str(cls, value):
        """
        Do not allow a string value to be empty.
        """
        if value == "":
            raise ValueError("Cannot be an empty string")
        return value

    @field_validator("identifier")
    @classmethod
    def empty_str_to_none(cls, value):
        """
        Coerce an empty string value to None.
        """
        if value == "":
            return None
        return value


class JobTemplateCloneRequest(BaseModel):
    """Schema for the request to clone a job template."""

    name: str | None = None
    identifier: str | None = None
    description: str | None = None
    template_vars: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def not_empty_str(cls, value):
        """
        Do not allow a string value to be empty.
        """
        if value == "":
            raise ValueError("Cannot be an empty string")
        return value

    @field_validator("identifier")
    @classmethod
    def empty_str_to_none(cls, value):
        """
        Coerce an empty string value to None.
        """
        if value == "":
            return None
        return value


class JobTemplateUpdateRequest(BaseModel):
    """Schema for the request to update a job template."""

    name: str | None = None
    identifier: str | None = None
    description: str | None = None
    template_vars: dict[str, Any] | None = None
    is_archived: bool | None = None

    @field_validator("name")
    @classmethod
    def not_empty_str(cls, value):
        """
        Do not allow a string value to be empty.
        """
        if value == "":
            raise ValueError("Cannot be an empty string")
        return value

    @field_validator("identifier")
    @classmethod
    def empty_str_to_none(cls, value):
        """
        Coerce an empty string value to None.
        """
        if value == "":
            return None
        return value


class TemplateFileDetailedView(BaseModel):
    """Schema for the response to get a template file."""

    parent_id: int
    filename: str
    file_type: str
    created_at: str
    updated_at: str


class WorkflowFileDetailedView(BaseModel):
    """Schema for the response to get a workflow file."""

    parent_id: int
    filename: str
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TableResource(BaseModel):
    """
    Describes a base for table models that include basic, common info.
    """

    id: int
    name: str
    owner_email: str
    created_at: str
    updated_at: str
    is_archived: bool
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobTemplateListView(TableResource):
    """Schema for the response to get a list of entries."""

    identifier: Optional[str] = None
    cloned_from_id: Optional[int] = None


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


EnvelopeT = TypeVar("EnvelopeT")


class ListResponseEnvelope(BaseModel, Generic[EnvelopeT]):
    """
    A model describing the structure of response envelopes from "list" endpoints.
    """

    items: list[EnvelopeT]
    total: int
    page: int
    size: int
    pages: int
