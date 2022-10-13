"""
Provide a convenience class for managing calls to S3.
"""
from functools import lru_cache
from pathlib import Path
from typing import Tuple, Type, Union

from boto3 import client
from botocore.client import BaseClient
from file_storehouse import (
    EngineS3,
    FileManager,
    FileManagerReadOnly,
    TransformationABC,
    TransformationCodecs,
)

from jobbergate_api.config import settings

IO_TRANSFORMATIONS = (TransformationCodecs("utf-8"),)
"""
Transformations to be performed when writing/reading S3 objects.

With this, all files are encoded/decoded with utf-8.

This constant can be shared between file managers.
"""


def engine_factory(*, s3_client: BaseClient, bucket_name: str, prefix: str) -> EngineS3:
    """
    Build an engine to manipulate objects from an s3 bucket.

    :param BaseClient s3_client: S3 client from boto3
    :param str bucket_name: The name of the s3 bucket
    :param str prefix: Prefix for object search at s3 (Work directory)
    :return EngineS3: And engine to manipulate files from s3
    """
    return EngineS3(s3_client=s3_client, bucket_name=bucket_name, prefix=prefix)


@lru_cache(maxsize=128)
def file_manager_factory(
    id: int,
    *,
    s3_client: BaseClient,
    bucket_name: str,
    work_directory: Path,
    manager_cls: Union[Type[FileManagerReadOnly], Type[FileManager]],
    transformations: Tuple[TransformationABC, ...],
) -> Union[FileManagerReadOnly, FileManager]:
    """
    Build a file managers on demand.

    :param int id: identification number
    :param BaseClient s3_client: S3 client from boto3
    :param str bucket_name: The name of the s3 bucket
    :param Path work_directory: Work directory (referred as prefix at boto3 documentation)
    :param Union[FileManager, FileManagerReadOnly] manager_cls: Manager class (i/o access or just read only)
    :param Tuple[TransformationABC] transformations: I/o transformations
    :return Union[FileManager, FileManagerReadOnly]: Manager object
    """
    return manager_cls(
        engine=engine_factory(
            s3_client=s3_client,
            bucket_name=bucket_name,
            prefix=f"{work_directory}/{id}/",
        ),
        io_transformations=transformations,
    )


s3_client = client("s3", endpoint_url=settings.S3_ENDPOINT_URL)
