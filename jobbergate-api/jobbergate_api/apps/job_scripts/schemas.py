"""
JobScript resource schema.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from jobbergate_api.apps.constants import FileType
from jobbergate_api.meta_mapper import MetaField, MetaMapper

job_script_meta_mapper = MetaMapper(
    id=MetaField(
        description="The unique database identifier for the instance",
        example=101,
    ),
    created_at=MetaField(
        description="The timestamp for when the instance was created",
        example="2021-12-28 23:13:00",
    ),
    updated_at=MetaField(
        description="The timestamp for when the instance was last updated",
        example="2021-12-28 23:52:00",
    ),
    job_script_name=MetaField(
        description="The unique name of the instance",
        example="test-job-script-88",
    ),
    job_script_description=MetaField(
        description="A text field providing a human-friendly description of the job_script",
        example="This job_scripts runs an Foo job using the bar variant",
    ),
    job_script_data_as_string=MetaField(
        description="The job_script itself. This is base64 encoded. Example below is decoded for clarity.",
        example=" ".join(
            [
                '{"application.sh": "#!/bin/bash\n\n#SBATCH --job-name=rats\n#SBATCH',
                "--partition=partition1\n#SBATCH --output=sample-%j.out\n\n\nsource",
                "/opt/openfoam8/etc/bashrc\n\nexport",
                'PATH=$PATH:/opt/openfoam8/platforms/linux64GccDPInt32Opt/bin\n\n\nblockMesh\nsimpleFoam"}',
            ]
        ),
    ),
    job_script_owner_email=MetaField(
        description="The email of the owner/creator of the instance",
        example="tucker@omnivector.solutions",
    ),
    application_id=MetaField(
        description="The foreign-key to the application from which this instance was created",
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
)


class JobScriptCreateRequest(BaseModel):
    """
    Request model for creating JobScript instances.
    """

    name: str
    description: Optional[str]

    class Config:
        schema_extra = job_script_meta_mapper


class RenderFromTemplateRequest(BaseModel):
    """Request model for creating a JobScript entry from a template."""

    entrypoint: str
    supporting_files: Optional[List[str]]
    sbatch_params: Optional[List[str]]
    param_dict: Dict[str, Any]

    class Config:
        schema_extra = job_script_meta_mapper


class JobScriptUpdateRequest(JobScriptCreateRequest):
    """
    Request model for updating JobScript instances.
    """

    class Config:
        schema_extra = job_script_meta_mapper


class JobScriptFile(BaseModel):
    """Model for the job_script_files field of the JobScript resource."""

    filename: str
    file_type: FileType

    class Config:
        orm_mode = True
        schema_extra = job_script_meta_mapper


class JobScriptResponse(BaseModel):
    """Model to match database for the JobScript resource."""

    id: Optional[int] = None
    name: str
    owner_email: str
    files: list[JobScriptFile]
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_template_id: Optional[int] = None

    class Config:
        orm_mode = True
        schema_extra = job_script_meta_mapper
