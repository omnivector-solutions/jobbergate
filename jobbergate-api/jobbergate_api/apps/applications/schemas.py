"""
Defines the schema for the resource Application.
"""
from datetime import datetime
from textwrap import dedent
from typing import Optional

from pydantic import BaseModel

from jobbergate_api.meta_mapper import MetaField, MetaMapper

application_meta_mapper = MetaMapper(
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
    application_name=MetaField(
        description="The unique name of the application",
        example="test-application-88",
    ),
    application_identifier=MetaField(
        description="A human-friendly label used for lookup on frequently accessed applications",
        example="App88",
    ),
    application_owner_email=MetaField(
        description="A long-form textual description of the application",
        example="tucker@omnivector.solutions",
    ),
    application_file=MetaField(
        description="The source code for the application file content text",
        example=dedent(
            """
            from jobbergate_cli.application_base import JobbergateApplicationBase
            from jobbergate_cli import appform


            class JobbergateApplication(JobbergateApplicationBase):

                def mainflow(self, data):
                    questions = []

                    questions.append(appform.List(
                        variablename="partition",
                        message="Choose slurm partition:",
                        choices=self.application_config['partitions'],
                    ))

                    questions.append(appform.Text(
                        variablename="job_name",
                        message="Please enter a jobname",
                        default=self.application_config['job_name']
                    ))
                    return questions
            """
        ).strip(),
    ),
    application_config=MetaField(
        description="Application config file content (.yaml) as text",
        example=dedent(
            """
            application_config:
              job_name: rats
              partitions:
              - juju-compute-SCqp
            jobbergate_config:
              default_template: test_job_script.sh
              output_directory: .
              supporting_files:
              - test_job_script.sh
              supporting_files_output_name:
                test_job_script.sh:
                - support_file_b.py
              template_files:
              - templates/test_job_script.sh
            """
        ).strip(),
    ),
    application_uploaded=MetaField(
        description="Indicates if the application file zip has been uploaded yet.",
        example=True,
    ),
)


class ApplicationCreateRequest(BaseModel):
    """
    Request model for creating Application instances.
    """

    application_name: str
    application_identifier: Optional[str]
    application_description: Optional[str] = None
    application_file: str
    application_config: str

    class Config:
        schema_extra = application_meta_mapper


class ApplicationUpdateRequest(BaseModel):
    """
    Request model for updating Application instances.
    """

    application_name: Optional[str]
    application_identifier: Optional[str]
    application_description: Optional[str]
    application_file: Optional[str]
    application_config: Optional[str]

    class Config:
        schema_extra = application_meta_mapper


class ApplicationResponse(BaseModel):
    """
    Complete model to match database for the Application resource.
    """

    id: int
    created_at: Optional[datetime] = datetime.utcnow()
    updated_at: Optional[datetime] = datetime.utcnow()
    application_name: str
    application_identifier: Optional[str]
    application_description: Optional[str]
    application_owner_email: str
    application_file: str
    application_config: str
    application_uploaded: bool

    class Config:
        orm_mode = True
        schema_extra = application_meta_mapper
