"""
Provide a convenience class for managing calls to S3.
"""
import tarfile
import typing
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import PurePath

from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, UploadFile, status
from file_storehouse import FileManager, FileManagerReadOnly, client  # type: ignore
from file_storehouse.engine import EngineS3  # type: ignore
from file_storehouse.key_mapping import KeyMappingNumeratedFolder, KeyMappingRaw  # type: ignore
from file_storehouse.transformation import TransformationCodecs  # type: ignore
from loguru import logger

from jobbergate_api.config import settings
from jobbergate_api.file_validation import perform_all_checks_on_uploaded_files


def get_s3_object_as_tarfile(s3man: FileManagerReadOnly, app_id: typing.Union[int, str]):
    """
    Return the tarfile of a S3 object.
    """
    logger.debug(f"Getting s3 object as tarfile {app_id=}")
    try:
        s3_application_obj = s3man[app_id]
    except (BotoCoreError, KeyError):
        message = f"Application with {app_id=} not found in S3"
        logger.error(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    s3_application_tar = tarfile.open(fileobj=BytesIO(s3_application_obj["Body"].read()))
    return s3_application_tar


@lru_cache
def application_template_manager_factory(
    application_id: typing.Union[int, str], is_read_only: bool = True
) -> typing.Union[FileManager, FileManagerReadOnly]:
    """
    Build a manager object for application template files.

    :param typing.Union[int, str] application_id: Application's id
    :param bool is_read_only: If the manager is read only or not, defaults to True
    :return typing.Union[FileManager, FileManagerReadOnly]: File manager
    """
    Manager = FileManagerReadOnly if is_read_only else FileManager
    return Manager(
        engine=EngineS3(
            s3_client,
            settings.S3_BUCKET_NAME,
            f"applications/{application_id}/templates/",
        ),
        transformation_list=[TransformationCodecs("utf-8")],
        key_mapping=KeyMappingRaw(),
    )


def write_application_files_to_s3(
    application_id: typing.Union[int, str],
    upload_files: typing.List[UploadFile],
    *,
    remove_previous_files: bool,
) -> None:
    """
    Write the list of uploaded application files to S3, fist checking them for consistency.

    :param typing.Union[int, str] application_id: Application identification number
    :param typing.List[UploadFile] upload_files: Uploaded files
    :param bool remove_previous_files: Delete old files before writing the new ones
    """
    logger.debug(f"Writing the list of uploaded files to S3: {application_id=}")

    perform_all_checks_on_uploaded_files(upload_files)

    if remove_previous_files:
        delete_application_files_from_s3(application_id)

    templates_manager = application_template_manager_factory(application_id, False)

    for file in upload_files:
        if file.filename.endswith(".py"):
            s3man_applications_source_files[application_id] = file.file
        elif file.filename.endswith((".j2", ".jinja2")):
            filename = PurePath(file.filename).name
            templates_manager[filename] = file.file


@dataclass
class ApplicationFiles:
    """
    Dataclass containing application files.
    """

    templates: typing.Dict[str, str]
    source_file: str


def get_application_files_from_s3(application_id: typing.Union[int, str]) -> ApplicationFiles:
    """
    Read the application files from S3.

    :param typing.Union[int, str] application_id: Application identification number
    :return ApplicationFiles: Application files
    """
    logger.debug(f"Getting application files from S3: {application_id=}")

    templates_manager = application_template_manager_factory(application_id, True)

    return ApplicationFiles(
        templates=dict(templates_manager), source_file=s3man_applications_source_files.get(application_id, "")
    )


def delete_application_files_from_s3(application_id: typing.Union[int, str]) -> None:
    """
    Delete the files associated to a given id from S3.

    :param typing.Union[int, str] application_id: Application identification number
    """
    logger.debug(f"Deleting from S3 the files associated to {application_id=}")

    templates_manager = application_template_manager_factory(application_id, False)
    templates_manager.clear()
    try:
        del s3man_applications_source_files[application_id]
    except KeyError:
        logger.warning(
            f"Tried to delete the source code for {application_id=}, but it was not found on S3",
        )


s3_client = client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
)

s3man_applications_source_files = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "applications"),
    transformation_list=[TransformationCodecs("utf-8")],
    key_mapping=KeyMappingNumeratedFolder("jobbergate.py"),
)

s3man_jobscripts = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "job-scripts"),
    transformation_list=[TransformationCodecs("utf-8")],
    key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
)
