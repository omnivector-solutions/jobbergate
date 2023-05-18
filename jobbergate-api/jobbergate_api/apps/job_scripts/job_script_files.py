"""
Provide a convenience class for managing job-script files.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

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


class JobScriptCreationError(Buzz):
    """Raise exception when facing any error creating a job-script from application files."""


def flatten_param_dict(param_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten an input dictionary to support the rendering process.

    See the example:

    >>> param_dict = {
    ...     "application_config": {"job_name": "rats", "partitions": [...]},
    ...     "jobbergate_config": {
    ...         "default_template": "test_job_script.sh",
    ...         "supporting_files": [...],
    ...         "supporting_files_output_name": {...},
    ...         "template_files": [...],
    ...         "job_script_name": None,
    ...         "output_directory": ".",
    ...         "partition": "debug",
    ...         "job_name": "rats",
    ...     },
    ... }
    >>> flat_param_dict = flatten_param_dict(param_dict)
    >>> print(flat_param_dict)
    {
        "job_name": "rats",
        "partitions": ["debug", "partition1"],
        "default_template": "test_job_script.sh",
        "supporting_files": ["test_job_script.sh"],
        "supporting_files_output_name": {"test_job_script.sh": [...]},
        "template_files": ["templates/test_job_script.sh"],
        "job_script_name": None,
        "output_directory": ".",
        "partition": "debug",
    }
    """
    param_dict_flat = {}
    for key, value in param_dict.items():
        if isinstance(value, dict):
            for nest_key, nest_value in value.items():
                param_dict_flat[nest_key] = nest_value
        else:
            param_dict_flat[key] = value
    return param_dict_flat


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    logger.debug("Preparing to inject sbatch params into job script")

    if not sbatch_params:
        logger.warning("Sbatch param list is empty")
        return job_script_data_as_string

    first_sbatch_index = job_script_data_as_string.find("#SBATCH")
    string_slice = job_script_data_as_string[first_sbatch_index:]
    line_end = string_slice.find("\n") + first_sbatch_index + 1

    inner_string = ""
    for parameter in sbatch_params:
        inner_string += "#SBATCH " + parameter + "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:line_end] + inner_string + job_script_data_as_string[line_end:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


class JobScriptFiles(BaseModel):
    """Model containing job-script files."""

    main_file_path: Path
    files: Dict[Path, str]

    @root_validator(pre=False, skip_on_failure=True)
    def check_main_file_path_is_in_files_keys(cls, values):
        """
        Validate the model.

        main_file_path should be found among the files.
        """
        if values["main_file_path"] not in values["files"].keys():
            raise ValueError("main_file_path is not a valid key on the dict files")
        return values

    @property
    def main_file(self):
        """
        Obtain the main file with this helper property.
        """
        return self.files.get(self.main_file_path)

    @classmethod
    def render_from_application(
        cls,
        application_files: ApplicationFiles,
        user_supplied_parameters: Dict[str, Any] | None = None,
        sbatch_params: List[str] | None = None,
    ):
        """Render JobScriptFiles from ApplicationFiles."""
        logger.debug("Rendering job-script files from an application")

        with JobScriptCreationError.check_expressions(
            main_message="One or more application files are missing",
        ) as check:
            check(application_files.config_file, "Application config file was not found")
            check(application_files.templates, "No template file was found")

        with JobScriptCreationError.handle_errors(
            "Error while parsing the config-file and/or job-script params",
        ):
            app_config = ApplicationConfig.get_from_yaml_file(
                application_files.config_file, user_supplied_parameters  # type: ignore
            )

        default_template_name: str = JobScriptCreationError.enforce_defined(
            app_config.jobbergate_config.default_template,
        )

        JobScriptCreationError.require_condition(
            default_template_name in application_files.templates,
            "Selected template {selected} not found in available templates: {templates}".format(
                selected=default_template_name,
                templates=", ".join(application_files.templates.keys()),
            ),
        )

        if app_config.jobbergate_config.supporting_files_output_name:
            with JobScriptCreationError.check_expressions(
                main_message="One or more supporting files are missing"
            ) as check:
                for supporting_file in app_config.jobbergate_config.supporting_files_output_name.keys():
                    check(supporting_file in application_files.templates, f"{supporting_file=} was not found")

        with JobScriptCreationError.handle_errors("Error rendering the main file"):
            param_dict_flat = flatten_param_dict(app_config.dict())

            output_directory: Optional[str] = app_config.jobbergate_config.output_directory

            # The output_directory can be None here if the Application *explicitly* sets it to None.
            if not output_directory:
                output_directory = "."

            main_file_path = Path(
                output_directory,
                default_template_name.rstrip(".j2").rstrip(".jinja2"),
            )

            main_file_content = Template(
                application_files.templates[default_template_name],
            ).render(data=param_dict_flat)

        with JobScriptCreationError.handle_errors("Error while injecting the sbatch params"):
            if sbatch_params:
                main_file_content = inject_sbatch_params(main_file_content, sbatch_params)

        with JobScriptCreationError.handle_errors("Error while creating JobScriptFiles object"):
            jobscript_files = cls(
                main_file_path=main_file_path,
                files={main_file_path: main_file_content},
            )

        with JobScriptCreationError.handle_errors("Error while rendering the supporting files"):
            output_name_mapping = app_config.jobbergate_config.supporting_files_output_name
            if output_name_mapping:
                for template_name, supporting_filename_list in output_name_mapping.items():
                    for supporting_filename in supporting_filename_list:
                        path = Path(output_directory, supporting_filename)

                        jobscript_files.files[path] = Template(
                            application_files.templates[template_name],
                        ).render(data=param_dict_flat)

        logger.debug("Done rendering job-script files from an application")

        return jobscript_files
