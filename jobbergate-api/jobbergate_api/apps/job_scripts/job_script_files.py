"""
Provide a convenience class for managing job-script files.
"""

from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict

from buzz import Buzz, require_condition
from file_storehouse import FileManager
from jinja2 import Template
from loguru import logger
from pydantic import BaseModel, root_validator

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.schemas import ApplicationConfig
from jobbergate_api.config import settings
from jobbergate_api.s3_manager import IO_TRANSFORMATIONS, file_manager_factory, s3_client

JOBSCRIPTS_WORK_DIR = "job-scripts"
JOBSCRIPTS_MAIN_FILE_FOLDER = "main-file"
JOBSCRIPTS_SUPPORTING_FILES_FOLDER = "supporting-files"

s3man_jobscripts_factory: Callable[[int], FileManager] = partial(
    file_manager_factory,
    s3_client=s3_client,
    bucket_name=settings.S3_BUCKET_NAME,
    work_directory=Path(JOBSCRIPTS_WORK_DIR),
    manager_cls=FileManager,
    transformations=IO_TRANSFORMATIONS,
)


class JobScriptCreationError(Buzz):
    """Raise exception when facing any error creating a job-script from application files."""


def flatten_param_dict(param_dict: Dict[str, Any]) -> Dict[str, Any]:
    param_dict_flat = {}
    for (key, value) in param_dict.items():
        if isinstance(value, dict):
            for nest_key, nest_value in value.items():
                param_dict_flat[nest_key] = nest_value
        else:
            param_dict_flat[key] = value
    return param_dict_flat


class JobScriptFiles(BaseModel):
    """
    Model containing job-script files.
    """

    main_file_path: Path
    files: Dict[Path, str]

    @root_validator(pre=False, skip_on_failure=True)
    def check_main_file_path_is_in_files_keys(cls, values):
        if values["main_file_path"] not in values["files"].keys():
            raise ValueError("main_file_path is not a valid key on the dict files")
        return values

    @classmethod
    def get_from_s3(cls, job_script_id: int):
        """
        Alternative method to initialize the model getting the objects from S3.
        """
        logger.debug(f"Getting job-script files from S3: {job_script_id=}")
        file_manager = s3man_jobscripts_factory(job_script_id)

        files = {}
        main_file_path = None
        main_file_counter = 0

        for s3_path in file_manager.keys():
            foldername = s3_path.parts[0]
            dict_path = s3_path.relative_to(foldername)
            if foldername == JOBSCRIPTS_MAIN_FILE_FOLDER:
                files[dict_path] = file_manager.get(s3_path)
                main_file_counter += 1
                main_file_path = dict_path
            elif foldername == JOBSCRIPTS_SUPPORTING_FILES_FOLDER:
                files[dict_path] = file_manager.get(s3_path)

        require_condition(
            main_file_counter == 1,
            f"One main file is expected for a job-script, found {main_file_counter}",
            ValueError,
        )

        return cls(main_file_path=main_file_path, files=files)

    @classmethod
    def delete_from_s3(cls, job_script_id: int):
        """
        Deleted the files associated with the given id.
        """
        logger.debug(f"Deleting from S3 the files associated to {job_script_id=}")
        file_manager = s3man_jobscripts_factory(job_script_id)
        file_manager.clear()
        logger.debug(f"Files were deleted for {job_script_id=}")

    def write_to_s3(self, job_script_id: int):
        logger.debug(f"Writing job-script files to S3: {job_script_id=}")

        file_manager = s3man_jobscripts_factory(job_script_id)

        for dict_path, content in self.files.items():
            if dict_path == self.main_file_path:
                s3_path = JOBSCRIPTS_MAIN_FILE_FOLDER / dict_path
            else:
                s3_path = JOBSCRIPTS_SUPPORTING_FILES_FOLDER / dict_path
            file_manager[s3_path] = content

        logger.debug("Done writing job-script files to S3")

    @classmethod
    def render_from_application(
        cls,
        application_files: ApplicationFiles,
        job_script_param_dict: Dict[str, Any],
    ):
        logger.debug("Rendering job-script files from an application")

        with JobScriptCreationError.check_expressions(
            main_message="One or more application files are missing",
        ) as check:
            check(application_files.config_file, "Application config file was not found")
            check(application_files.source_file, "Application source file was not found")
            check(application_files.templates, "No template file was found")

        with JobScriptCreationError.handle_errors(
            "Error while parsing the config-file and/or job-script params",
        ):
            app_config = ApplicationConfig.get_from_yaml_file(
                application_files.config_file, job_script_param_dict
            )

        with JobScriptCreationError.check_expressions(
            main_message=(
                "One or more template files are missing "
                "the available options are: "
                ", ".join(application_files.templates.keys()),
            ),
        ) as check:
            default_template_name = app_config.jobbergate_config.default_template
            check(
                default_template_name in application_files.templates,
                f"{default_template_name=} was not found",
            )
            if app_config.jobbergate_config.supporting_files_output_name:
                for supporting_file in app_config.jobbergate_config.supporting_files_output_name.keys():
                    check(supporting_file in application_files.templates, f"{supporting_file=} was not found")

        param_dict_flat = flatten_param_dict(app_config.dict())

        main_file_path = Path(
            app_config.jobbergate_config.output_directory,
            default_template_name.rstrip(".j2").rstrip(".jinja2"),
        )

        jobscript_files = cls(
            main_file_path=main_file_path,
            files={
                main_file_path: render_template(
                    application_files.templates[default_template_name],
                    param_dict_flat,
                ),
            },
        )

        if app_config.jobbergate_config.supporting_files_output_name:
            output_name_mapping = app_config.jobbergate_config.supporting_files_output_name
        else:
            output_name_mapping = {}

        for template_name, supporting_filename_list in output_name_mapping.items():

            for supporting_filename in supporting_filename_list:
                path = Path(
                    app_config.jobbergate_config.output_directory,
                    supporting_filename,
                )

                jobscript_files.files[path] = render_template(
                    application_files.templates[template_name],
                    param_dict_flat,
                )

        return jobscript_files


def render_template(template_file, params):
    template = Template(template_file)
    return template.render(data=params)
