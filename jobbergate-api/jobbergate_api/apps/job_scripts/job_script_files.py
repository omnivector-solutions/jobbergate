"""
Provide a convenience class for managing job-script files.
"""

from pathlib import Path
from typing import Any, Dict, List, cast

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
    for (key, value) in param_dict.items():
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
    """
    Model containing job-script files.

    The folder structure aims to mimic the one specified by the application code.
    In this way, the ``output_directory`` and file names for the main file
    and supporting files are application specific.

    To differentiate the files, they are stored in two folders, ``main-file`` and
    ``supporting-files`` and the paths used in this model are relative the those
    folders. See the example:

        job-scripts
        └───<id>
            └───main-file
            │   └───<output-directory>
            │       └───<main-file-name>
            │
            └───supporting-files
                └───<output-directory>
                    │   <supporting-file-name-1>
                    │   <supporting-file-name-2>
                    │   <supporting-file-name-3>
                    └───...

    In this way, services that consume this information can maintain the
    structure as well (like the user interface and the agents).
    """

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
    def get_from_s3(cls, job_script_id: int):
        """
        Alternative method to initialize the model getting the objects from S3.
        """
        logger.debug(f"Getting job-script files from S3: {job_script_id=}")
        file_manager = cls.file_manager_factory(job_script_id)

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
            f"One and only one main file is expected for a job-script, found {main_file_counter}",
            ValueError,
        )

        jobscript_files = cls(main_file_path=main_file_path, files=files)

        logger.debug(f"Done getting job-script files from S3: {job_script_id=}")

        return jobscript_files

    @classmethod
    def delete_from_s3(cls, job_script_id: int):
        """
        Delete the files associated with the given id.
        """
        file_manager = cls.file_manager_factory(job_script_id)
        logger.debug(
            f"Deleting from S3 the files associated to {job_script_id=}. "
            f"Files to be deleted: {', '.join(map(str, file_manager.keys()))}"
        )
        file_manager.clear()
        logger.debug(f"Files were deleted for {job_script_id=}")

    def write_to_s3(self, job_script_id: int, *, remove_previous_files: bool = True):
        """
        Write to s3 the files associated with a given id.
        """
        logger.debug(f"Writing job-script files to S3: {job_script_id=}")

        if remove_previous_files:
            self.delete_from_s3(job_script_id)

        file_manager = self.file_manager_factory(job_script_id)

        for dict_path, content in self.files.items():
            if dict_path == self.main_file_path:
                s3_path = JOBSCRIPTS_MAIN_FILE_FOLDER / dict_path
            else:
                s3_path = JOBSCRIPTS_SUPPORTING_FILES_FOLDER / dict_path
            file_manager[s3_path] = content

        logger.debug(f"Done writing job-script files to S3 for {job_script_id=}")

    @classmethod
    def render_from_application(
        cls,
        application_files: ApplicationFiles,
        user_supplied_parameters: Dict[str, Any] = None,
        sbatch_params: List[str] = None,
    ):
        """
        Render JobScriptFiles from ApplicationFiles.
        """
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
                application_files.config_file, user_supplied_parameters  # type: ignore
            )

        default_template_name: str = JobScriptCreationError.enforce_defined(
            app_config.jobbergate_config.default_template,
        )

        if default_template_name.startswith("templates/"):
            (_, default_template_name) = default_template_name.split("/", maxsplit=1)

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

            main_file_path = Path(
                app_config.jobbergate_config.output_directory,
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
                        path = Path(
                            app_config.jobbergate_config.output_directory,
                            supporting_filename,
                        )

                        jobscript_files.files[path] = Template(
                            application_files.templates[template_name],
                        ).render(data=param_dict_flat)

        logger.debug("Done rendering job-script files from an application")

        return jobscript_files

    @classmethod
    def file_manager_factory(self, job_script_id: int) -> FileManager:
        """
        Build an application file manager.
        """
        return cast(
            FileManager,
            file_manager_factory(
                id=job_script_id,
                s3_client=s3_client,
                bucket_name=settings.S3_BUCKET_NAME,
                work_directory=Path(JOBSCRIPTS_WORK_DIR),
                manager_cls=FileManager,
                transformations=IO_TRANSFORMATIONS,
            ),
        )
