"""
Provides a convenience class for managing calls to S3.
"""
import tarfile
import typing
from collections.abc import MutableMapping
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, status
from loguru import logger

from jobbergate_api.config import settings


class S3Manager(MutableMapping):
    """
    Provide a class for managing the files from an S3 client.

    This class implements the MutableMapping protocol, so all interactions with
    S3 can be done using a dict-like interface.

    The files stored in the Bucket defined at settings and with a key template
    computed internally in this class.

    Note: According to boto3's documentation, `list_objects` returns some or
    all (up to 1,000) of the objects in a bucket. Something to pay attention
    to in a production environment, since some functionality that depends on
    this method may not see all the files there (like __iter__ and __len__).
    """

    def __init__(self, s3_client, folder: str, filename: str):
        """
        Initialize an s3 manager. The interaction with S3 is done with the
        provided client, folder and filename.
        """
        self.s3_client = s3_client
        self.folder_name = folder
        self.filename = filename
        self.key_template = f"{self.folder_name}/{{app_id}}/{self.filename}"
        self.bucket_name = settings.S3_BUCKET_NAME

    def __getitem__(self, app_id: typing.Union[int, str]) -> str:
        """
        Get a file from the client associated to the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Getting from S3: {key})")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

        return response.get("Body").read().decode("utf-8")

    def __setitem__(self, app_id: typing.Union[int, str], file: str) -> None:
        """
        Upload a file to the client for the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Uploading to S3: {key})")

        try:
            self.s3_client.put_object(Body=file, Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    def __delitem__(self, app_id: typing.Union[int, str]) -> None:
        """
        Delete a file from the client associated to the given id.
        """
        key = self._get_key_from_id(app_id)
        logger.debug(f"Deleting from S3: {key})")

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    def __iter__(self) -> typing.Iterable:
        """
        Yield all ids found in the work folder.
        """
        response = self._get_list_of_objects()
        for key in response:
            yield self._get_app_id_from_key(key.get("Key"))

    def __len__(self) -> int:
        """
        Count the number of ids found in the work folder.
        """
        response = self._get_list_of_objects()
        return len(response)

    def _get_key_from_id(self, app_id: typing.Union[int, str]) -> str:
        """
        Get an s3 key based upon the app_id. If app_id is empty, throw an exception.
        """
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You must supply a non-empty app_id: got ({app_id=})",
            )
        return self.key_template.format(app_id=app_id)

    def _get_app_id_from_key(self, key: str) -> str:
        """
        Get the app_id based upon an s3 key.
        """
        return key.lstrip(f"{self.folder_name}/").rstrip(f"/{self.filename}")

    def _get_list_of_objects(self) -> list:
        """
        Return the list of files found in the work folder.
        Raise 404 when facing connection errors or if the response is not
        in the expected format.
        """
        try:
            return self.s3_client.list_objects(
                Bucket=self.bucket_name,
                Prefix=self.folder_name,
            ).get("Contents")
        except (BotoCoreError, KeyError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not possible to retrieve information from S3",
            )


def get_s3_object_as_tarfile(s3man: S3Manager, app_id: typing.Union[int, str]):
    """
    Return the tarfile of a S3 object.
    """
    try:
        s3_application_obj = s3man[app_id]
    except (BotoCoreError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={app_id} not found in S3",
        )

    s3_application_tar = tarfile.open(fileobj=BytesIO(s3_application_obj.get("Body").read()))
    return s3_application_tar


s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
s3man_applications = S3Manager(s3_client, "applications", "jobbergate.tar.gz")
s3man_jobscripts = S3Manager(s3_client, "job-scripts", "jobbergate.tar.gz")
