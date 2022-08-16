"""
Provide a convenience class for managing calls to S3.
"""
import typing
from dataclasses import dataclass, field
from pathlib import PurePath

from fastapi import UploadFile
from file_storehouse import FileManager, FileManagerReadOnly, client
from file_storehouse.engine.s3 import BaseClient, EngineS3
from file_storehouse.key_mapping import KeyMappingNumeratedFolder, KeyMappingRaw
from file_storehouse.transformation import TransformationABC, TransformationCodecs
from loguru import logger

from jobbergate_api.config import settings
from jobbergate_api.file_validation import perform_all_checks_on_uploaded_files

LIST_OF_TRANSFORMATIONS: typing.List[TransformationABC] = [TransformationCodecs("utf-8")]
"""
List the transformations to be performed when writing/reading S3 objects.

This constant can be shared between file managers.
"""


@dataclass
class ApplicationFiles:
    """
    Dataclass containing application files.
    """

    templates: typing.Dict[str, str]
    source_file: str


@dataclass
class ApplicationFileManager:
    """
    Manager for application files, designed to handle application source code and templates on S3.
    """

    bucket_name: str
    s3_client: BaseClient
    source_files: FileManager = field(init=False, repr=False)

    def __post_init__(self):
        """
        Post-init method to compute additional fields in the class.
        """
        self.source_files = FileManager(
            engine=EngineS3(self.s3_client, self.bucket_name, "applications"),
            transformation_list=LIST_OF_TRANSFORMATIONS,
            key_mapping=KeyMappingNumeratedFolder("jobbergate.py"),
        )

    def template_manager_factory(
        self, application_id: int, is_read_only: bool = True
    ) -> typing.Union[FileManager, FileManagerReadOnly]:
        """
        Build a manager object for application template files.

        :param int application_id: Application's id
        :param bool is_read_only: If the manager is read only or not, defaults to True
        :return typing.Union[FileManager, FileManagerReadOnly]: File manager
        """
        Manager = FileManagerReadOnly if is_read_only else FileManager
        return Manager(
            engine=EngineS3(
                self.s3_client,
                self.bucket_name,
                f"applications/{application_id}/templates/",
            ),
            transformation_list=LIST_OF_TRANSFORMATIONS,
            key_mapping=KeyMappingRaw(),
        )

    def write_to_s3(
        self,
        application_id: int,
        upload_files: typing.List[UploadFile],
        *,
        remove_previous_files: bool = False,
    ):
        """
        Write the list of uploaded application files to S3, fist checking them for consistency.

        :param int application_id: Application identification number
        :param typing.List[UploadFile] upload_files: Uploaded files
        :param bool remove_previous_files: Delete old files before writing the new ones
        """
        logger.debug(f"Writing the list of uploaded files to S3: {application_id=}")

        perform_all_checks_on_uploaded_files(upload_files)

        if remove_previous_files:
            self.delete_from_s3(application_id)

        templates_manager = typing.cast(
            FileManager,
            self.template_manager_factory(application_id, is_read_only=False),
        )

        for upload in upload_files:
            if upload.filename.endswith(".py"):
                self.source_files[application_id] = upload.file
            elif upload.filename.endswith((".j2", ".jinja2")):
                filename = PurePath(upload.filename).name
                templates_manager[filename] = upload.file

    def get_from_s3(self, application_id: int) -> ApplicationFiles:
        """
        Read the application files from S3.

        :param int application_id: Application identification number
        :return ApplicationFiles: Application files
        """
        logger.debug(f"Getting application files from S3: {application_id=}")

        templates_manager = self.template_manager_factory(application_id, True)

        return ApplicationFiles(
            templates=dict(templates_manager),
            source_file=self.source_files.get(application_id, ""),
        )

    def delete_from_s3(self, application_id: int):
        """
        Delete the files associated to a given id from S3.

        :param int application_id: Application identification number
        """
        logger.debug(f"Deleting from S3 the files associated to {application_id=}")

        templates_manager = typing.cast(
            FileManager, self.template_manager_factory(application_id, is_read_only=False)
        )

        templates_manager.clear()
        try:
            del self.source_files[application_id]
        except KeyError:
            logger.warning(
                f"Tried to delete the source code for {application_id=}, but it was not found on S3",
            )


s3_client = client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
)

s3man_applications = ApplicationFileManager(bucket_name=settings.S3_BUCKET_NAME, s3_client=s3_client)

s3man_jobscripts = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "job-scripts"),
    transformation_list=LIST_OF_TRANSFORMATIONS,
    key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
)
