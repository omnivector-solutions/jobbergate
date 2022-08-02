"""
Provide a convenience class for managing calls to S3.
"""
import tarfile
import typing
from functools import lru_cache
from io import BytesIO

from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, status
from file_storehouse import FileManager, FileManagerReadOnly, client  # type: ignore
from file_storehouse.engine import EngineS3  # type: ignore
from file_storehouse.key_mapping import KeyMappingNumeratedFolder, KeyMappingRaw  # type: ignore
from file_storehouse.transformation import TransformationCodecs  # type: ignore
from loguru import logger

from jobbergate_api.config import settings


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
def application_manager_factory(
    application_id: typing.Union[int, str], is_read_only: bool = True
) -> typing.Union[FileManager, FileManagerReadOnly]:
    """
    Build a manager object for application files.

    :param typing.Union[int, str] application_id: Application's id
    :param bool is_read_only: If the manager is read only or not, defaults to True
    :return typing.Union[FileManager, FileManagerReadOnly]: File manager
    """
    Manager = FileManagerReadOnly if is_read_only else FileManager
    return Manager(
        engine=EngineS3(
            s3_client,
            settings.S3_BUCKET_NAME,
            f"applications/{application_id}/",
        ),
        key_mapping=KeyMappingRaw(),
    )


s3_client = client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
)

s3man_applications = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "applications"),
    transformation_list=[TransformationCodecs("utf-8")],
    key_mapping=KeyMappingNumeratedFolder("jobbergate.py"),
)

s3man_jobscripts = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "job-scripts"),
    transformation_list=[TransformationCodecs("utf-8")],
    key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
)
