"""
Provides a convenience class for managing calls to S3.
"""
import re

import boto3
import snick
from loguru import logger

from slurp.config import settings, DatabaseEnv
from slurp.exceptions import SlurpException


class S3Manager:
    """
    This class prepares the bucket_name and s3 key template from project settings. It
    also initializes an s3 client. It's methods are thin wrappers around s3 calls but
    provide the mappings for buckets and keys.
    """

    def __init__(self, db_env=DatabaseEnv.NEXTGEN):
        self.db_env = db_env
        self.bucket_name = self.get_env("S3_BUCKET_NAME")
        self.key_template = (
            f"jobbergate-resources/{{owner_id}}/applications/{{app_id}}/jobbergate.tar.gz"
            if db_env is DatabaseEnv.LEGACY
            else f"applications/{{app_id}}/jobbergate.tar.gz"
        )

        self.url = self.get_env("S3_ENDPOINT_URL")
        access_key_id = self.get_env("AWS_ACCESS_KEY_ID")
        secret_access_key = self.get_env("AWS_SECRET_ACCESS_KEY")
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,

        )

    def get_env(self, env_suffix):
        key = f"{self.db_env}_{env_suffix}"
        SlurpException.require_condition(
            key in settings.schema()["properties"].keys(),
            f"Trying to access unknown setting {key}",
        )
        return getattr(settings, key)


    def get_key(self, app_id, owner_id=None):
        """
        Render a s3 key from the template given an app_id.

        For legacy s3, you need to supply owner_id as well.
        """
        return self.key_template.format(app_id=app_id, owner_id=owner_id)

    def put(self, key, obj):
        """
        Put an object at the given key.
        """
        self.s3_client.put_object(
            Body=obj, Bucket=self.bucket_name, Key=key,
        )

    def get(self, key):
        """
        Get an object at the given key.
        """
        return self.s3_client.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()

    def list_keys(self):
        """
        List all keys in the client's bucket.
        """
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix="jobbergate-resources"):
            try:
                contents = page["Contents"]
            except KeyError:
                break

            for obj in contents:
                yield obj["Key"]

    def ensure_bucket(self):
        """
        Ensure that the bucket exists. Skip creation if it alreayd exists.
        """
        SlurpException.require_condition(
            self.db_env is not DatabaseEnv.LEGACY,
            "Cannot create legacy bucket",
        )
        logger.debug(f"Ensuring bucket {self.bucket_name} exists at {self.url}")
        with SlurpException.handle_errors(
            self.s3_client.exceptions.BucketAlreadyExists,
            re_raise=False,
            do_except=lambda *_: logger.debug(f"Bucket {self.bucket_name} already exists. Skipping creation"),
        ):
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            logger.debug(f"Bucket {self.bucket_name} created")


    def clear_bucket(self):
        """
        Clear all objects from the bucket.
        """
        logger.debug(f"Clearing bucket {self.bucket_name} in {self.url}")
        SlurpException.require_condition(
            self.db_env is not DatabaseEnv.LEGACY,
            "Cannot clear legacy bucket",
        )
        with SlurpException.handle_errors(
            self.s3_client.exceptions.NoSuchBucket,
            re_raise=False,
            do_except=lambda *_: logger.debug(f"No such bucket {self.bucket_name}"),
        ):
            for key in self.list_keys():
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        logger.debug("Finished clearing bucket")


def transfer_s3(source_s3man, target_s3man, applications_map=None):
    """
    Transfer data from legacy s3 bucket to nextgen s3 bucket.

    If the application_id in the legacy s3 key name doesn't exist in our application
    map, skip the object. If the legacy s3 key doesn't match the expected pattern, skip
    the object. Otherwise put the object into the nextgen s3 bucket with the application
    id mapped to the appropriate nextgen application.
    """
    SlurpException.require_condition(
        target_s3man.db_env is not DatabaseEnv.LEGACY,
        "Cannot transfer to legacy S3",
    )
    logger.debug(
        snick.unwrap(
            f"""
            Transfering S3 data from {source_s3man.db_env}
            to {target_s3man.db_env} store")
            """
        )
    )
    target_s3man.ensure_bucket()
    bad_pattern_skips = 0
    missing_id_skips = 0
    successful_transfers = 0
    mapper = lambda x: applications_map.get(int(x)) if applications_map else lambda x: x
    for source_key in source_s3man.list_keys():
        match = re.search(r'applications/(\d+)', source_key)
        if not match:
            bad_pattern_skips += 1
            continue
        source_application_id = match.group(1)
        target_application_id = mapper(source_application_id)
        if not target_application_id:
            missing_id_skips += 1
            continue
        target_obj = source_s3man.get(source_key)
        target_key = target_s3man.get_key(target_application_id)
        target_s3man.put(target_key, target_obj)
        successful_transfers += 1
    logger.debug(f"Skipped {bad_pattern_skips} objects due to unparsable key")
    logger.debug(f"Skipped {missing_id_skips} objects due to missing application_id")
    logger.debug(f"Finished transfering {successful_transfers} objects")
