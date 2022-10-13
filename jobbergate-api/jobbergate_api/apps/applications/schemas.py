"""
Defines the schema for the resource Application.
"""
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, root_validator
from yaml import safe_load

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


class JobbergateConfig(BaseModel):
    """
    Model for Jobbergate configuration (subsection at the yaml file).
    """

    default_template: Optional[str]
    supporting_files: Optional[List[str]]
    supporting_files_output_name: Optional[Dict[str, List[str]]]
    template_files: Optional[List[str]]
    job_script_name: Optional[str]
    output_directory: Optional[str] = "."

    @root_validator(pre=True)
    def compute_extra_settings(cls, values):
        """
        Compute missing values and extra operations to enhance the user experience.
        """
        # Transform string to list of strings for a better user experience
        if values.get("supporting_files_output_name"):
            for k, v in values["supporting_files_output_name"].items():
                if isinstance(v, str):
                    values["supporting_files_output_name"][k] = [v]

        # Get the list of supporting files automatically
        if values.get("supporting_files_output_name") and not values.get("supporting_files"):
            values["supporting_files"] = list(values.get("supporting_files_output_name"))

        return values

    class Config:
        extra = "allow"


class ApplicationConfig(BaseModel):
    """
    Model for application configuration, used to parse the yaml file.
    """

    application_config: Dict[str, Any]
    jobbergate_config: JobbergateConfig

    @classmethod
    def get_from_yaml_file(
        cls, yaml_file: Union[bytes, str], user_supplied_parameters: Dict[str, Any] = None
    ):
        """
        Construct this model from the application config file (jobbergate.yaml).

        User supplied parameters can be supplied to override the defaults at the file.
        """
        param_dict = safe_load(yaml_file)
        if user_supplied_parameters:
            param_dict.update(**user_supplied_parameters)
        return cls(**param_dict)


class ApplicationCreateRequest(BaseModel):
    """
    Request model for creating Application instances.
    """

    application_name: str
    application_identifier: Optional[str]
    application_description: Optional[str] = None

    class Config:
        schema_extra = application_meta_mapper


class ApplicationUpdateRequest(BaseModel):
    """
    Request model for updating Application instances.
    """

    application_name: Optional[str]
    application_identifier: Optional[str]
    application_description: Optional[str]
    application_config: Optional[str]

    class Config:
        schema_extra = application_meta_mapper


class ApplicationPartialResponse(BaseModel):
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
    application_uploaded: bool

    class Config:
        orm_mode = True
        schema_extra = application_meta_mapper


class ApplicationResponse(ApplicationPartialResponse):
    """
    Complete model to match database for the Application resource.
    """

    application_config: Optional[str]
    application_source_file: Optional[str]
    application_templates: Optional[Dict[str, str]]

    class Config:
        orm_mode = True
        schema_extra = application_meta_mapper
