"""
Provides a convenience class for managing calls to S3.
"""
import tarfile
import typing
from abc import ABC, abstractmethod
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, UploadFile, status

from jobbergate_api.config import settings


class BucketClientBase(ABC):
    """
    Base class used to describe how to interact with bucket clients.
    """

    @abstractmethod
    def put(self, file: typing.IO, key: str) -> None:
        """
        Upload a file to the client for the given key.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete a file from the client associated to the given key.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> typing.IO:
        """
        Get a file from the client associated to the given key.
        """
        pass


class DummyClient(BucketClientBase):
    def __init__(self):
        """
        Initialize an dummy client.
        """
        self.client = {}

    def put(self, file: typing.IO, key: str) -> None:
        """
        Upload a file to the client for the given key.
        """
        self.client[key] = file

    def delete(self, key: str) -> None:
        """
        Delete a file from the client associated to the given key.
        """
        try:
            del self.client[key]
        except KeyError:
            raise KeyError(f"No such key: {key}")

    def get(self, key: str) -> typing.IO:
        """
        Get a file from the client associated to the given key.
        """
        try:
            return self.client[key]
        except KeyError:
            raise KeyError(f"No such key: {key}")


class S3Client(BucketClientBase):
    def __init__(self):
        """
        Initialize an s3 client.
        """
        self.bucket_name = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

    def put(self, file: typing.IO, key: str) -> None:
        """
        Upload a file to the client for the given key.
        """
        self.s3_client.put_object(
            Body=file,
            Bucket=self.bucket_name,
            Key=key,
        )

    def delete(self, key: str) -> None:
        """
        Delete a file from the client associated to the given key.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchBucket:
            raise KeyError(f"No such bucket: {self.bucket_name}")
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    def get(self, key: str) -> typing.IO:
        """
        Get a file from the client associated to the given key.
        """
        return self.s3_client.get_object(Bucket=self.bucket_name, Key=key)


class S3Manager:
    """
    Provide a class for managing connection to an S3 bucket.

    Prepares the bucket_name and s3 key template from project settings. Also initialize an s3
    client. Provide methods as thin wrappers around s3 calls but provide the mappings for buckets and keys.
    """

    def __init__(self, directory_name: str = "applications", client: BucketClientBase = None):
        """
        Initialize the S3Manager class instance.
        """
        self.key_template = directory_name + "/{app_id}/jobbergate.tar.gz"

        if client is None:
            client = S3Client()

        self.client = client

    def _get_key(self, app_id: str) -> str:
        """
        Get an s3 key based upon the app_id. If app_id is empty, throw an exception.
        """
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You must supply a non-empty app_id: got ({app_id=})",
            )
        return self.key_template.format(app_id=app_id)

    def put(self, upload_file: UploadFile, app_id: str = "") -> str:
        """
        Upload a file to s3 for the given app_id and returns its key.
        """
        key = self._get_key(app_id)
        self.client.put(upload_file.file, key)
        return key

    def delete(self, app_id: str = ""):
        """
        Delete a file from s3 associated to the given app_id.
        """
        self.client.delete(key=self._get_key(app_id))

    def get(self, app_id: str = ""):
        """
        Get a file from s3 associated to the given app_id.
        """
        return self.client.get(key=self._get_key(app_id))

    def get_s3_object_as_tarfile(self, application_id):
        """
        Return the tarfile of a S3 object.
        """
        try:
            s3_application_obj = self.get(app_id=application_id)
        except BotoCoreError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with id={application_id} not found in S3",
            )
        s3_application_tar = tarfile.open(fileobj=BytesIO(s3_application_obj["Body"].read()))
        return s3_application_tar
