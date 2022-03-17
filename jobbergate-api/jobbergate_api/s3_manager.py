"""
Provides a convenience class for managing calls to S3.
"""

import boto3
from fastapi import HTTPException, UploadFile, status

from jobbergate_api.config import settings


class S3Manager:
    """
    Provide a class for managing connection to an S3 bucket.

    Prepares the bucket_name and s3 key template from project settings. Also initialize an s3
    client. Provide methods as thin wrappers around s3 calls but provide the mappings for buckets and keys.
    """

    def __init__(self):
        """
        Initialize the S3Manager class instance.
        """
        self.bucket_name = settings.S3_BUCKET_NAME
        self.key_template = "applications/{app_id}/jobbergate.tar.gz"
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def _get_key(self, app_id):
        """
        Get an s3 key based upon the app_id. If app_id is falsey, throw an exception.
        """
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You must supply a non-empty app_id: got ({app_id=})",
            )
        return self.key_template.format(app_id=app_id)

    def put(self, upload_file: UploadFile, app_id: str = ""):
        """
        Upload a file to s3 for the given app_id and returns the.
        """
        key = self._get_key(app_id)
        self.s3_client.put_object(
            Body=upload_file.file, Bucket=self.bucket_name, Key=key,
        )
        return key

    def delete(self, app_id: str = ""):
        """
        Delete a file from s3 associated to the given app_id.
        """
        key = self._get_key(app_id)
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchBucket:
            raise KeyError(f"No such bucket: {self.bucket_name}")
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    def get(self, app_id: str = ""):
        """
        Get a file from s3 associated to the given app_id.
        """
        return self.s3_client.get_object(Bucket=self.bucket_name, Key=self._get_key(app_id))
