"""
Provide a convenience class for managing calls to S3.
"""
from typing import Dict, Optional, List, Tuple, Union, Callable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path, PurePath

from fastapi import UploadFile
from file_storehouse import FileManager, FileManagerReadOnly, client
from file_storehouse.engine.s3 import BaseClient, EngineS3
from file_storehouse.key_mapping import KeyMappingNumeratedFolder, KeyMappingRaw
from file_storehouse.transformation import TransformationABC, TransformationCodecs
from loguru import logger
from pydantic import BaseModel, Field

from jobbergate_api.config import settings
from jobbergate_api.file_validation import perform_all_checks_on_uploaded_files

LIST_OF_TRANSFORMATIONS: Tuple[TransformationABC] = (TransformationCodecs("utf-8"),)
"""
List the transformations to be performed when writing/reading S3 objects.

This constant can be shared between file managers.
"""


def engine_factory(*, s3_client: BaseClient, bucket_name: str, work_directory: Path) -> EngineS3:
    return EngineS3(s3_client=s3_client, bucket_name=bucket_name, prefix=str(work_directory))


def file_manager_factory(
    id: int,
    *,
    s3_client: BaseClient,
    bucket_name: str,
    work_directory: Path,
    manager_cls: Union[FileManager, FileManagerReadOnly],
    transformations: Tuple[TransformationABC],
) -> Union[FileManager, FileManagerReadOnly]:

    return manager_cls(
        engine=engine_factory(
            s3_client=s3_client,
            bucket_name=bucket_name,
            work_directory=work_directory / str(id),
        ),
        transformation_list=transformations,
    )


s3_client = client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
)

s3man_applications_factory: Callable[[int], FileManager] = partial(
    file_manager_factory,
    s3_client=s3_client,
    bucket_name=settings.S3_BUCKET_NAME,
    work_directory=Path("applications"),
    manager_cls=FileManager,
    transformations=LIST_OF_TRANSFORMATIONS,
)

s3man_jobscripts_factory: Callable[[int], FileManager] = partial(
    file_manager_factory,
    s3_client=s3_client,
    bucket_name=settings.S3_BUCKET_NAME,
    work_directory=Path("job-scripts"),
    manager_cls=FileManager,
    transformations=LIST_OF_TRANSFORMATIONS,
)


APPLICATION_SOURCE_FILE_NAME: str = "jobbergate.py"
APPLICATION_TEMPLATE_FOLDER: str = "templates"


class ApplicationFiles(BaseModel):
    """
    Model containing application files.
    """

    source_file: Optional[str] = None
    templates: Optional[Dict[str, str]] = Field(default_factory=dict)

    @classmethod
    def get_from_s3(cls, application_id: int):
        logger.debug(f"Getting application files from S3: {application_id=}")
        file_manager = s3man_applications_factory(application_id)

        application_files = cls(
            source_file=file_manager.get(APPLICATION_SOURCE_FILE_NAME),
        )

        for path in file_manager.keys():
            if path.parent == APPLICATION_TEMPLATE_FOLDER:
                filename = path.name
                application_files.templates[filename] = file_manager[path]

        return application_files

    @classmethod
    def delete_from_s3(cls, application_id: int):
        logger.debug(f"Deleting from S3 the files associated to {application_id=}")
        file_manager = s3man_applications_factory(application_id)
        file_manager.clear()

    def write_to_s3(self, application_id: int, *, remove_previous_files: bool = True):
        logger.debug(f"Writing the application files to S3: {application_id=}")

        if remove_previous_files:
            self.delete_from_s3(application_id)

        file_manager = s3man_applications_factory(application_id)

        if self.source_file:
            path = Path(APPLICATION_SOURCE_FILE_NAME)
            file_manager[path] = self.source_file

        for name, content in self.templates.items():
            path = Path(APPLICATION_TEMPLATE_FOLDER, name)
            file_manager[path] = content

    @classmethod
    def get_from_upload_files(cls, upload_files: List[UploadFile]):
        logger.debug("Getting application files from the uploaded files")

        perform_all_checks_on_uploaded_files(upload_files)

        application_files = cls()

        for upload in upload_files:
            if upload.filename.endswith(".py"):
                application_files.source_file = upload.file.read().decode("utf-8")
                upload.file.seek(0)
            elif upload.filename.endswith((".j2", ".jinja2")):
                filename = PurePath(upload.filename).name
                application_files.templates[filename] = upload.file.read().decode("utf-8")
                upload.file.seek(0)

        return application_files


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
    ) -> Union[FileManager, FileManagerReadOnly]:
        """
        Build a manager object for application template files.

        :param int application_id: Application's id
        :param bool is_read_only: If the manager is read only or not, defaults to True
        :return Union[FileManager, FileManagerReadOnly]: File manager
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
        upload_files: List[UploadFile],
        *,
        remove_previous_files: bool = False,
    ):
        """
        Write the list of uploaded application files to S3, fist checking them for consistency.

        :param int application_id: Application identification number
        :param List[UploadFile] upload_files: Uploaded files
        :param bool remove_previous_files: Delete old files before writing the new ones
        """
        ApplicationFiles.get_from_upload_files(upload_files).write_to_s3(
            application_id,
            remove_previous_files=remove_previous_files,
        )

    def get_from_s3(self, application_id: int) -> ApplicationFiles:
        """
        Read the application files from S3.

        :param int application_id: Application identification number
        :return ApplicationFiles: Application files
        """
        logger.debug(f"Getting application files from S3: {application_id=}")

        return ApplicationFiles.get_from_s3(application_id)

    def delete_from_s3(self, application_id: int):
        """
        Delete the files associated to a given id from S3.

        :param int application_id: Application identification number
        """
        ApplicationFiles.delete_from_s3(application_id)


s3man_applications = ApplicationFileManager(bucket_name=settings.S3_BUCKET_NAME, s3_client=s3_client)

s3man_jobscripts = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "job-scripts"),
    transformation_list=LIST_OF_TRANSFORMATIONS,
    key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
)
