"""
JobScript resource schema.
"""
from datetime import datetime
from textwrap import dedent
from typing import Any

from pydantic import BaseModel

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateListView
from jobbergate_api.apps.schemas import TableResource
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_script_meta_mapper = MetaMapper(
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
    description=MetaField(
        description="A text field providing a human-friendly description of the job_script",
        example="This job_scripts runs an Foo job using the bar variant",
    ),
    owner_email=MetaField(
        description="The email of the owner/creator of the instance",
        example="tucker@omnivector.solutions",
    ),
    parent_template_id=MetaField(
        description="The foreign-key to the job script template from which this instance was created",
        example=71,
    ),
    sbatch_params=MetaField(
        description="SBATCH parameters to inject into the job_script",
        example=["alpha", "beta", "delta"],
    ),
    param_dict=MetaField(
        description="Parameters to use when rendering the job_script jinja2 template",
        example={"param1": 7, "param2": 13},
    ),
    template_output_name_mapping=MetaField(
        description=dedent(
            """
            A mapping of template names to file names.
            The first element is the entrypoint, the others are optional support files.
            """
        ).strip(),
        example={"template.py.jinja2": "template.py", "support.json.jinja2": "support.json"},
    ),
    filename=MetaField(
        description="The name of the file",
        example="job-script.py",
    ),
    file_type=MetaField(
        description="The type of the file",
        example=FileType.ENTRYPOINT.value,
    ),
    is_archived=MetaField(
        description="Indicates if the job script has been archived.",
        example=False,
    ),
)


class JobScriptCreateRequest(BaseModel):
    """
    Request model for creating JobScript instances.
    """

    name: str
    description: str | None

    class Config:
        schema_extra = job_script_meta_mapper


class RenderFromTemplateRequest(BaseModel):
    """Request model for creating a JobScript entry from a template."""

    template_output_name_mapping: dict[str, str]
    sbatch_params: list[str] | None
    param_dict: dict[str, Any]

    class Config:
        schema_extra = job_script_meta_mapper


class JobScriptUpdateRequest(BaseModel):
    """
    Request model for updating JobScript instances.
    """

    name: str | None
    description: str | None
    is_archived: bool | None

    class Config:
        schema_extra = job_script_meta_mapper


class JobScriptFileDetailedView(BaseModel):
    """Model for the job_script_files field of the JobScript resource."""

    parent_id: int
    filename: str
    file_type: FileType
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True
        schema_extra = job_script_meta_mapper


class JobScriptListView(TableResource):
    """Model to match database for the JobScript resource."""

    parent_template_id: int | None
    template: JobTemplateListView | None

    class Config:
        schema_extra = job_script_meta_mapper


class JobScriptDetailedView(JobScriptListView):
    """Model to match database for the JobScript resource."""

    files: list[JobScriptFileDetailedView] | None
