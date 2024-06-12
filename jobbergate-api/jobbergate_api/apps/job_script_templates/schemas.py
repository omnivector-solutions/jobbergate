"""
Provide schemas for the job script templates component.
"""

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.schemas import LengthLimitedStr, TableResource
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_template_meta_mapper = MetaMapper(
    id=MetaField(
        description="The unique database identifier for the instance",
        example=101,
    ),
    parent_id=MetaField(
        description="The unique database identifier for the parent of this instance",
        example=101,
    ),
    created_at=MetaField(
        description="The timestamp for when the instance was created",
        example="2023-08-18T13:55:37.172285",
    ),
    updated_at=MetaField(
        description="The timestamp for when the instance was last updated",
        example="2023-08-18T13:55:37.172285",
    ),
    name=MetaField(
        description="The unique name of the instance",
        example="test-job-script-88",
    ),
    identifier=MetaField(
        description="A human-friendly label used for lookup on frequently accessed applications",
        example="App88",
    ),
    description=MetaField(
        description="A text field providing a human-friendly description of the job_script",
        example="This job_scripts runs an Foo job using the bar variant",
    ),
    owner_email=MetaField(
        description="The email of the owner/creator of the instance",
        example="tucker@omnivector.solutions",
    ),
    template_vars=MetaField(
        description="The template variables of the job script template",
        example={"param1": 7, "param2": 13},
    ),
    runtime_config=MetaField(
        description="The runtime configuration of the workflow",
        example={"param1": 7, "param2": 13},
    ),
    filename=MetaField(
        description="The name of the file",
        example="job-script.py",
    ),
    file_type=MetaField(
        description="The type of the file",
        example=FileType.ENTRYPOINT.value,
    ),
    template_files=MetaField(
        description="The template files attached to a job script template",
    ),
    workflow_file=MetaField(
        description="The workflow file attached to a job script template",
    ),
    is_archived=MetaField(
        description="Indicates if the job script template has been archived.",
        example=False,
    ),
    cloned_from_id=MetaField(
        description="Indicates the id this entry has been cloned from, if any.",
        example=101,
    ),
)


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

    model_config = ConfigDict(extra="allow", json_schema_extra=job_template_meta_mapper)


class JobTemplateCreateRequest(BaseModel):
    """Schema for the request to create a job template."""

    name: LengthLimitedStr
    identifier: LengthLimitedStr | None = None
    description: LengthLimitedStr | None = None
    template_vars: dict[LengthLimitedStr, Any] | None = None

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

    model_config = ConfigDict(json_schema_extra=job_template_meta_mapper)


class JobTemplateCloneRequest(BaseModel):
    """Schema for the request to clone a job template."""

    name: LengthLimitedStr | None = None
    identifier: LengthLimitedStr | None = None
    description: LengthLimitedStr | None = None
    template_vars: dict[LengthLimitedStr, Any] | None = None

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

    model_config = ConfigDict(json_schema_extra=job_template_meta_mapper)


class JobTemplateUpdateRequest(BaseModel):
    """Schema for the request to update a job template."""

    name: LengthLimitedStr | None = None
    identifier: LengthLimitedStr | None = None
    description: LengthLimitedStr | None = None
    template_vars: dict[LengthLimitedStr, Any] | None = None
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

    model_config = ConfigDict(json_schema_extra=job_template_meta_mapper)


class TemplateFileDetailedView(BaseModel):
    """Schema for the response to get a template file."""

    parent_id: int
    filename: str
    file_type: FileType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra=job_template_meta_mapper)


class WorkflowFileDetailedView(BaseModel):
    """Schema for the response to get a workflow file."""

    parent_id: int
    filename: str
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, json_schema_extra=job_template_meta_mapper)


class JobTemplateListView(TableResource):
    """Schema for the response to get a list of entries."""

    identifier: Optional[str] = None
    cloned_from_id: Optional[int] = None

    model_config = ConfigDict(json_schema_extra=job_template_meta_mapper)


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
