"""
Provide a convenience class for managing calls to S3.
"""
import re
import tarfile
import typing
from collections.abc import MutableMapping
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, status
from loguru import logger

from jobbergate_api.config import settings


def read_only_protection(function: typing.Callable) -> typing.Callable:
    """
    Use this decorator to warp key methods at the s3 manager.

    It aims to protect the files from been overwritten or deleted when the s3 manager
    is set as read-only. Raise RuntimeError if any protected operation is tried.
    """

    def helper(s3man, *args, **kwargs):

        if s3man.read_only:
            message = "Illegal operation for a read-only S3 manager (folder={}, bucket={}).".format(
                s3man.folder_name, s3man.bucket_name
            )
            logger.error(message)
            raise RuntimeError(message)
        function(s3man, *args, **kwargs)

    return helper


class S3ManagerRaw(MutableMapping):
    """
    Provide a class for managing the binary files from an S3 client.

    This class implements the MutableMapping protocol, so all interactions with
    S3 can be done using a dict-like interface.

    The files stored in the Bucket defined at settings and with a key template
    computed internally in this class.
    """

    def __init__(
        self, s3_client, folder: str, filename: str, *, bucket_name: str = None, read_only: bool = False
    ):
        """
        Initialize a s3 manager.

        The interaction with S3 is done with the provided client, folder and filename.
        """
        self.s3_client = s3_client
        self.folder_name = folder
        self.filename = filename
        self.bucket_name = bucket_name if bucket_name else settings.S3_BUCKET_NAME
        self.read_only = read_only

        self._key_template = f"{self.folder_name}/{{app_id}}/{self.filename}"
        self._get_id_re = re.compile(r"/(?P<id>\d+)/{filename}$".format(filename=self.filename))

        logger.info(
            f"Initializing S3Manager at the bucket={self.bucket_name} for key_template={self._key_template}"
        )

    def __getitem__(self, app_id: typing.Union[int, str]):
        """
        Get a file from the client associated to the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Getting from S3: {key}")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"No such key: {key}")
            raise KeyError(f"No such key: {key}")

        return response

    @read_only_protection
    def __setitem__(self, app_id: typing.Union[int, str], file: bytes) -> None:
        """
        Upload a file to the client for the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Uploading to S3: {key})")

        try:
            self.s3_client.put_object(Body=file, Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"No such key: {key}")
            raise KeyError(f"No such key: {key}")

    @read_only_protection
    def __delitem__(self, app_id: typing.Union[int, str]) -> None:
        """
        Delete a file from the client associated to the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Deleting from S3: {key})")

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"No such key: {key}")
            raise KeyError(f"No such key: {key}")

    def __iter__(self) -> typing.Iterator[str]:
        """
        Yield all ids found in the work folder.
        """
        for key in self._get_list_of_objects():
            yield self._get_app_id_from_key(key)

    def __len__(self) -> int:
        """
        Count the number of keys found in the work folder.
        """
        return sum(1 for _ in self._get_list_of_objects())

    def _get_key_from_id(self, app_id: typing.Union[int, str]) -> str:
        """
        Get an s3 key based upon the app_id. If app_id is empty, throw an exception.
        """
        if not str(app_id):
            message = f"You must supply a non-empty app_id: got ({app_id=})"
            logger.warning(message)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        return self._key_template.format(app_id=app_id)

    def _get_app_id_from_key(self, key: str) -> str:
        """
        Get the app_id based upon an s3 key.
        """
        match = re.search(self._get_id_re, key)
        if not match:
            message = f"Impossible to get id from {key=}"
            logger.error(message)
            raise ValueError(message)
        return match.group("id")

    def _get_list_of_objects(self) -> typing.Iterable[str]:
        """
        Yield the keys found in the work folder.

        Raise 404 when facing connection errors.
        """
        logger.debug(
            f"Listing the objects at the bucket={self.bucket_name} for key_template={self._key_template}"
        )
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.folder_name):
                contents = page.get("Contents", [])
                if not contents:
                    break
                for obj in contents:
                    yield obj["Key"]
        except BotoCoreError:
            message = "Not possible to retrieve information from S3"
            logger.error(message)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

    @read_only_protection
    def clear(self):
        """
        Clear all objects from work folder in this bucket.
        """
        logger.info(
            f"Clearing the objects at the bucket={self.bucket_name} for key_template={self._key_template}"
        )
        super().clear()


class S3ManagerText(S3ManagerRaw):
    """
    Provide a class for managing the text files from an S3 client.

    This class implements the MutableMapping protocol, so all interactions with
    S3 can be done using a dict-like interface.

    The files stored in the Bucket defined at settings and with a key template
    computed internally in this class.
    """

    DECODE_SPEC = "utf-8"

    def __getitem__(self, app_id: typing.Union[int, str]) -> str:
        """
        Get a file from the client associated to the given id.
        """
        response = super().__getitem__(app_id)
        return response["Body"].read().decode(self.DECODE_SPEC)

    def __setitem__(self, app_id: typing.Union[int, str], file: str) -> None:
        """
        Upload a file to the client for the given id.
        """
        super().__setitem__(app_id, file.encode(self.DECODE_SPEC))


def get_s3_object_as_tarfile(s3man: S3ManagerRaw, app_id: typing.Union[int, str]):
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


s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
)
s3man_applications = S3ManagerRaw(s3_client, "applications", "jobbergate.tar.gz")
s3man_jobscripts = S3ManagerText(s3_client, "job-scripts", "jobbergate.txt")
