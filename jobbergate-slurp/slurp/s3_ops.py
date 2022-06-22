"""
Provides a convenience class for managing calls to S3.
"""
from collections import namedtuple
import re
import typing
from collections.abc import MutableMapping

import boto3
from botocore.exceptions import BotoCoreError
from loguru import logger

from slurp.config import settings
from slurp.exceptions import SlurpException


class S3Manager(MutableMapping):
    """
    Provide a class for managing the files from an S3 client.

    This class implements the MutableMapping protocol, so all interactions with
    S3 can be done using a dict-like interface.

    The files stored in the Bucket defined at settings and with a key template
    computed internally in this class.
    """

    def __init__(
        self,
        s3_client,
        folder: str,
        filename: str,
        *,
        bucket_name: str = None,
        read_only: bool = True,
        key_template: str = None,
    ):
        """
        Initialize an s3 manager. The interaction with S3 is done with the
        provided client, folder and filename.
        """
        self.s3_client = s3_client
        self.folder_name = folder
        self.filename = filename
        self.key_template = key_template
        self.bucket_name = bucket_name
        self.read_only = read_only

    def read_only_protection(function):
        """
        A decorator used to warp key methods, aiming to protect the files from
        been overwritten or deleted when the s3 manger is set as read-only.
        Raise RuntimeError if any protected operation is tried.
        """

        def helper(self, *args, **kwargs):

            if self.read_only:
                message = "Illegal operation for a read-only S3 manager (folder={}, bucket={})."
                raise RuntimeError(message.format(self.folder_name, self.bucket_name))
            function(self, *args, **kwargs)

        return helper

    def __getitem__(self, key: str) -> str:
        """
        Get a file from the client associated to the given id.
        """
        logger.trace(f"Getting from S3: {key})")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

        return response.get("Body").read()

    @read_only_protection
    def __setitem__(self, key: str, file: str) -> None:
        """
        Upload a file to the client for the given id.
        """
        logger.trace(f"Uploading to S3: {key})")

        try:
            self.s3_client.put_object(Body=file, Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    @read_only_protection
    def __delitem__(self, key: str) -> None:
        """
        Delete a file from the client associated to the given id.
        """
        logger.trace(f"Deleting from S3: {key})")

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.s3_client.exceptions.NoSuchKey:
            raise KeyError(f"No such key: {key}")

    def __iter__(self) -> typing.Iterable[str]:
        """
        Yield all ids found in the work folder.
        """
        yield from self.get_list_of_objects()

    def __len__(self) -> int:
        """
        Count the number of keys found in the work folder.
        """
        return sum(1 for _ in self.get_list_of_objects())

    def get_key_from_id(self, app_id: typing.Union[int, str]) -> str:
        """
        Get an s3 key based upon the app_id. If app_id is empty, throw an exception.
        """
        if not str(app_id):
            raise RuntimeError(f"You must supply a non-empty app_id: got ({app_id=})")
        return self.key_template.format(app_id=app_id)

    def get_app_id_from_key(self, key: str) -> str:
        """
        Get the app_id based upon an s3 key.
        """
        return key.lstrip(f"{self.folder_name}/").rstrip(f"/{self.filename}")

    def get_list_of_objects(self) -> typing.Iterable[str]:
        """
        Yield the keys found in the work folder.
        Raise 404 when facing connection errors.
        """
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.folder_name):
                contents = page.get("Contents", [])
                if not contents:
                    break
                for obj in contents:
                    yield obj["Key"]
        except BotoCoreError:
            raise RuntimeError("Not possible to retrieve information from S3")

    @read_only_protection
    def clear(self):
        """
        Clear all objects from work folder in this bucket.
        """
        logger.info(f"Clearing folder {self.folder_name} in the bucket {self.bucket_name}")
        super().clear()

    @read_only_protection
    def ensure_bucket(self):
        """
        Ensure that the bucket exists. Skip creation if it already exists.
        """
        logger.debug(f"Ensuring bucket {self.bucket_name} exists.")
        with SlurpException.handle_errors(
            self.s3_client.exceptions.BucketAlreadyExists,
            re_raise=False,
            do_except=lambda *_: logger.debug(f"Bucket {self.bucket_name} already exists. Skipping creation"),
        ):
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} created")


def build_managers():

    db_gen = namedtuple("db_generation", "legacy nextgen")

    client = db_gen(
        legacy=boto3.client(
            "s3",
            endpoint_url=settings.LEGACY_S3_ENDPOINT_URL,
            aws_access_key_id=settings.LEGACY_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.LEGACY_AWS_SECRET_ACCESS_KEY,
        ),
        nextgen=boto3.client(
            "s3",
            endpoint_url=settings.NEXTGEN_S3_ENDPOINT_URL,
            aws_access_key_id=settings.NEXTGEN_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.NEXTGEN_AWS_SECRET_ACCESS_KEY,
        ),
    )

    s3man = db_gen(
        legacy=S3Manager(
            client.legacy,
            "jobbergate-resources",
            "jobbergate.tar.gz",
            bucket_name=settings.LEGACY_S3_BUCKET_NAME,
            key_template="jobbergate-resources/{owner_id}/applications/{app_id}/jobbergate.tar.gz",
            read_only=True,
        ),
        nextgen=S3Manager(
            client.nextgen,
            "applications",
            "jobbergate.tar.gz",
            bucket_name=settings.NEXTGEN_S3_BUCKET_NAME,
            key_template="applications/{app_id}/jobbergate.tar.gz",
            read_only=False,
        ),
    )

    return s3man


def transfer_s3(s3man, applications_map):
    """
    Transfer data from legacy s3 bucket to nextgen s3 bucket.

    If the application_id in the legacy s3 key name doesn't exist in our application
    map, skip the object. If the legacy s3 key doesn't match the expected pattern, skip
    the object. Otherwise put the object into the nextgen s3 bucket with the application
    id mapped to the appropriate nextgen application.
    """
    logger.info("Transferring S3 data from legacy to nextgen store")
    s3man.nextgen.ensure_bucket()
    bad_pattern_skips = 0
    missing_id_skips = 0
    successful_transfers = 0
    transferred_ids = []
    for legacy_key in s3man.legacy.keys():
        match = re.search(r"applications/(\d+)", legacy_key)
        if not match:
            bad_pattern_skips += 1
            logger.warning(f"Bad pattern: {legacy_key=}")
            continue
        legacy_application_id = match.group(1)
        nextgen_application_id = applications_map.get(int(legacy_application_id))
        if not nextgen_application_id:
            missing_id_skips += 1
            logger.warning(f"Missing id: {legacy_key=}")
            continue

        legacy_obj = s3man.legacy.get(legacy_key)
        nextgen_key = s3man.nextgen.get_key_from_id(nextgen_application_id)
        s3man.nextgen[nextgen_key] = legacy_obj
        transferred_ids.append(nextgen_application_id)
        successful_transfers += 1
        logger.trace(f"Successful transfer: {legacy_key=}")

    logger.info(f"Skipped {bad_pattern_skips} objects due to unparsable key")
    logger.info(f"Skipped {missing_id_skips} objects due to missing application_id")
    logger.info(f"Finished transferring {successful_transfers} objects")

    return transferred_ids
