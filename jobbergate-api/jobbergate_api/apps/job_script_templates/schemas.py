"""
Provide schemas for the job script templates component.
"""

import json
from datetime import datetime
from typing import Any, Optional

import pydantic
from pydantic import BaseModel

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.schemas import TableResource
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
)


class RunTimeConfig(BaseModel):
    """
    Schema for the runtime config of a job template.

    Notice this includes user supplied variables, so it has no predefined field.
    It also loads the contend directly from the json at the request payload.
    """

    @classmethod
    def __get_validators__(cls):
        """
        Get the validators.
        """
        yield cls.validate_to_json

    @classmethod
    def validate_to_json(cls, value):
        """
        Validate the produced json.
        """
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

    class Config:
        extra = pydantic.Extra.allow
        schema_extra = job_template_meta_mapper


class JobTemplateCreateRequest(BaseModel):
    """Schema for the request to create a job template."""

    name: str
    identifier: str | None
    description: str | None
    template_vars: dict[str, Any] | None

    class Config:
        schema_extra = job_template_meta_mapper


class JobTemplateUpdateRequest(BaseModel):
    """Schema for the request to update a job template."""

    name: str | None
    identifier: str | None
    description: str | None
    template_vars: dict[str, Any] | None
    is_archived: bool | None

    class Config:
        schema_extra = job_template_meta_mapper


class TemplateFileDetailedView(BaseModel):
    """Schema for the response to get a template file."""

    parent_id: int
    filename: str
    file_type: FileType
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        schema_extra = job_template_meta_mapper


class WorkflowFileDetailedView(BaseModel):
    """Schema for the response to get a workflow file."""

    parent_id: int
    filename: str
    runtime_config: Optional[dict[str, Any]] = {}
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
        schema_extra = job_template_meta_mapper


class JobTemplateListView(TableResource):
    """Schema for the response to get a list of entries."""

    identifier: Optional[str]

    class Config:
        schema_extra = job_template_meta_mapper


class JobTemplateDetailedView(JobTemplateListView):
    """
    Schema for the request to an entry.

    Notice the files default to None, as they are not always requested, to differentiate between
    an empty list when they are requested, but no file is found.
    """

    template_vars: dict[str, Any] | None

    template_files: list[TemplateFileDetailedView] | None
    workflow_files: list[WorkflowFileDetailedView] | None
