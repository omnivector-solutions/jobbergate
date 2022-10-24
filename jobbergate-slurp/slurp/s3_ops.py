"""
Provides a convenience class for managing calls to S3.
"""
import asyncio
import contextlib
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Set

import aioboto3
from buzz import check_expressions, handle_errors, require_condition
from loguru import logger

from slurp.config import settings

APPLICATIONS_WORK_DIR = "applications"
APPLICATION_CONFIG_FILE_NAME = "jobbergate.yaml"
APPLICATION_SOURCE_FILE_NAME = "jobbergate.py"
APPLICATION_TEMPLATE_FOLDER = "templates"


@contextlib.asynccontextmanager
async def s3_bucket(is_legacy: bool = True):

    if is_legacy:
        endpoint_url = settings.LEGACY_S3_ENDPOINT_URL
        bucket_name = settings.LEGACY_S3_BUCKET_NAME
        key_id = settings.LEGACY_AWS_ACCESS_KEY_ID
        access_key = settings.LEGACY_AWS_SECRET_ACCESS_KEY
    else:
        endpoint_url = settings.NEXTGEN_S3_ENDPOINT_URL
        bucket_name = settings.NEXTGEN_S3_BUCKET_NAME
        key_id = settings.NEXTGEN_AWS_ACCESS_KEY_ID
        access_key = settings.NEXTGEN_AWS_SECRET_ACCESS_KEY

    session = aioboto3.Session(aws_access_key_id=key_id, aws_secret_access_key=access_key)

    async with session.resource("s3", endpoint_url=endpoint_url) as s3:
        bucket = await s3.Bucket(bucket_name)
        yield bucket


@contextlib.contextmanager
def extract_tarball(legacy_object):

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with tarfile.open(fileobj=BytesIO(legacy_object), mode="r:gz") as tar:
            tar.extractall(tmp_path)

        yield tmp_path


def get_id_from_legacy_s3_key(key: str) -> int:

    with handle_errors(f"Error extraction application id and user id from: {key}"):
        splitted = key.split("/")
        user = int(splitted[1])
        id = int(splitted[3])

    return id


def check_application_files(work_dir: Path):
    with check_expressions("Check application files") as check:
        for file in [APPLICATION_CONFIG_FILE_NAME, APPLICATION_SOURCE_FILE_NAME]:
            check((work_dir / file).is_file(), f"File {file} was not found")
        check(
            len(list((work_dir / APPLICATION_TEMPLATE_FOLDER).glob("*"))) >= 1,
            "No template file was found",
        )


async def transfer_application_files(legacy_applications) -> Set[int]:

    logger.info("Start migrating application files to s3")

    legacy_application_ids = {application["id"] for application in legacy_applications}

    async def transfer_helper(s3_object, nextgen_bucket):
        id = get_id_from_legacy_s3_key(s3_object.key)

        require_condition(
            id in legacy_application_ids,
            f"Missing application_id={id} (files on S3 but id not on the database)",
        )

        with handle_errors(f"Error retrieving object from legacy bucket: {s3_object.key}"):

            s3_legacy_object = await s3_object.get()
            s3_legacy_content = await s3_legacy_object["Body"].read()

        key = f"{APPLICATIONS_WORK_DIR}/{id}/"

        with handle_errors(f"Error manipulating the files from: {s3_object.key}"):

            with extract_tarball(s3_legacy_content) as work_dir:

                check_application_files(work_dir)

                for file in [APPLICATION_CONFIG_FILE_NAME, APPLICATION_SOURCE_FILE_NAME]:
                    await nextgen_bucket.upload_file(work_dir / file, key + file)

                template_folder = work_dir / APPLICATION_TEMPLATE_FOLDER
                for template in template_folder.rglob("*"):
                    await nextgen_bucket.upload_file(
                        template,
                        f"{key}{APPLICATION_TEMPLATE_FOLDER}/{template.name}",
                    )

            return id

    async with s3_bucket(is_legacy=True) as legacy_bucket:
        async with s3_bucket(is_legacy=False) as nextgen_bucket:

            prefix = "jobbergate-resources/"

            tasks = [
                asyncio.create_task(transfer_helper(s3_object, nextgen_bucket))
                async for s3_object in legacy_bucket.objects.filter(Prefix=prefix)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Exception):
                    logger.warning(str(r))

            transferred_ids = {i for i in results if isinstance(i, int)}

            logger.success(f"Finished migrating {len(transferred_ids)} applications to s3")

            return list(transferred_ids)
