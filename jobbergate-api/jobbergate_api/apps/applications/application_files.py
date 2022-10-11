"""
Provide a convenience class for managing application files.
"""

from pathlib import Path, PurePath
from typing import Dict, List, Optional, cast

from fastapi import UploadFile
from file_storehouse import FileManager
from loguru import logger
from pydantic import BaseModel, Field

from jobbergate_api.apps.applications.constants import (
    APPLICATION_CONFIG_FILE_NAME,
    APPLICATION_SOURCE_FILE_NAME,
    APPLICATION_TEMPLATE_FOLDER,
    APPLICATIONS_WORK_DIR,
)
from jobbergate_api.apps.applications.file_validation import perform_all_checks_on_uploaded_files
from jobbergate_api.config import settings
from jobbergate_api.s3_manager import IO_TRANSFORMATIONS, file_manager_factory, s3_client


def _get_template_files(file_manager: FileManager) -> Dict[str, str]:
    """
    Filter the template files out of the file manager.
    """
    template_paths = filter(lambda path: str(path.parent) == APPLICATION_TEMPLATE_FOLDER, file_manager.keys())

    return {path.name: file_manager[path] for path in template_paths}


class ApplicationFiles(BaseModel):
    """
    Model containing application files.
    """

    config_file: Optional[str] = Field(None, alias="application_config")
    source_file: Optional[str] = Field(None, alias="application_source_file")
    templates: Dict[str, str] = Field(default_factory=dict, alias="application_templates")

    class Config:
        allow_population_by_field_name = True

    @classmethod
    def get_from_s3(cls, application_id: int):
        """
        Alternative method to initialize the model getting the objects from S3.
        """
        logger.debug(f"Getting application files from S3: {application_id=}")
        file_manager = cls.file_manager_factory(application_id)

        logger.debug(
            f"The number of files available for {application_id=} is {len(file_manager)}. "
            f"They are: {', '.join(map(str, file_manager.keys()))}"
        )

        application_files = cls(
            config_file=file_manager.get(APPLICATION_CONFIG_FILE_NAME),
            source_file=file_manager.get(APPLICATION_SOURCE_FILE_NAME),
            templates=_get_template_files(file_manager),
        )

        if not application_files.config_file:
            logger.warning(f"Application config file was not found for {application_id=}")
        if not application_files.source_file:
            logger.warning(f"Application source file was not found for {application_id=}")
        if not application_files.templates:
            logger.warning(f"No template file was found for {application_id=}")

        logger.debug("Success getting application files from S3")

        return application_files

    @classmethod
    def delete_from_s3(cls, application_id: int):
        """
        Delete the files associated with the given id.
        """
        file_manager = cls.file_manager_factory(application_id)
        logger.debug(
            f"Deleting from S3 the files associated to {application_id=}. "
            f"Files to be deleted: {', '.join(map(str, file_manager.keys()))}"
        )
        file_manager.clear()
        logger.debug(f"Files were deleted for {application_id=}")

    def write_to_s3(self, application_id: int, *, remove_previous_files: bool = True):
        """
        Write to s3 the files associated with a given id.
        """
        logger.debug(f"Writing the application files to S3: {application_id=}")

        if remove_previous_files:
            self.delete_from_s3(application_id)

        file_manager = self.file_manager_factory(application_id)

        if self.config_file:
            path = Path(APPLICATION_CONFIG_FILE_NAME)
            file_manager[path] = self.config_file

        if self.source_file:
            path = Path(APPLICATION_SOURCE_FILE_NAME)
            file_manager[path] = self.source_file

        for name, content in self.templates.items():
            path = Path(APPLICATION_TEMPLATE_FOLDER, name)
            file_manager[path] = content

        logger.debug(f"Files were written for {application_id=}")

    @classmethod
    def get_from_upload_files(cls, upload_files: List[UploadFile]):
        """
        Initialize the model getting the objects from a list of uploaded files.
        """
        logger.debug("Getting application files from the uploaded files")

        perform_all_checks_on_uploaded_files(upload_files)

        application_files = cls()

        for upload in upload_files:
            file_data = upload.file.read().decode("utf-8")
            upload.file.seek(0)
            if upload.filename == APPLICATION_SOURCE_FILE_NAME:
                application_files.source_file = file_data
            elif upload.filename == APPLICATION_CONFIG_FILE_NAME:
                application_files.config_file = file_data
            elif upload.filename.endswith((".j2", ".jinja2")):
                filename = PurePath(upload.filename).name
                application_files.templates[filename] = file_data

        logger.debug("Success getting application files from the uploaded files")

        return application_files

    @classmethod
    def file_manager_factory(self, application_id: int) -> FileManager:
        """
        Build an application file manager.
        """
        return cast(
            FileManager,
            file_manager_factory(
                id=application_id,
                s3_client=s3_client,
                bucket_name=settings.S3_BUCKET_NAME,
                work_directory=Path(APPLICATIONS_WORK_DIR),
                manager_cls=FileManager,
                transformations=IO_TRANSFORMATIONS,
            ),
        )
