"""
Provides a convenience class for managing calls to S3.
"""

import boto3

from jobbergateapi2.config import settings
from fastapi import UploadFile


class S3Manager:
    """
    This clas prepares the bucket_name and s3 key template from project settings. It also initializes an s3
    client. It's methods are thin wrappers around s3 calls but provide the mappings for buckets and keys.
    """

    def __init__(self):
        self.bucket_name = "jobbergateapi2-{stage}-{region}-resources".format(
            stage=settings.SERVERLESS_STAGE,
            region=settings.SERVERLESS_REGION,
        )
        self.key_template = f"{settings.S3_BASE_PATH}/{{owner_id}}/applications/{{app_id}}/jobbergate.tar.gz"
        self.s3_client = boto3.client("s3")

    def _get_key(self, owner_id, app_id):
        """
        Get an s3 key based upon the owner_id and app_id. If either are falsey, throw an exception.
        """
        if not owner_id or not app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You must supply a non-empty owner_id and app_id: got ({owner_id=}, {app_id=})"
            )
        return self.key_template.format(owner_id=owner_id, app_id=app_id)

    def put(self, upload_file: UploadFile, owner_id: str = "", app_id: str = ""):
        """
        Upload a file to s3 for the given owner_id and app_id.
        """
        self.s3_client.put_object(
            Body=upload_file.file,
            Bucket=self.bucket_name,
            Key=self._get_key(owner_id, app_id),
        )

    def delete(self, owner_id: str = "", app_id: str = ""):
        """
        Delete a file from s3 associated to the given owner_id and app_id.
        """
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=self._get_key(owner_id, app_id))
