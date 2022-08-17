"""
Provides a convenience class for managing calls to S3.
"""
import contextlib
import tarfile
import tempfile
from collections import namedtuple
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from file_storehouse import FileManager, FileManagerReadOnly, client
from file_storehouse.engine.s3 import EngineS3
from file_storehouse.key_mapping import KeyMappingNumeratedFolder
from jobbergate_api.s3_manager import LIST_OF_TRANSFORMATIONS, ApplicationFileManager
from loguru import logger

from slurp.config import settings


def build_managers():

    db_gen = namedtuple("db_generation", "legacy nextgen")
    s3_folder = namedtuple("Folder", "applications jobscripts")

    s3_client = db_gen(
        legacy=client(
            "s3",
            endpoint_url=settings.LEGACY_S3_ENDPOINT_URL,
            aws_access_key_id=settings.LEGACY_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.LEGACY_AWS_SECRET_ACCESS_KEY,
        ),
        nextgen=client(
            "s3",
            endpoint_url=settings.NEXTGEN_S3_ENDPOINT_URL,
            aws_access_key_id=settings.NEXTGEN_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.NEXTGEN_AWS_SECRET_ACCESS_KEY,
        ),
    )

    s3man = s3_folder(
        applications=db_gen(
            legacy=FileManagerReadOnly(
                engine=EngineS3(
                    s3_client.legacy,
                    settings.LEGACY_S3_BUCKET_NAME,
                    "jobbergate-resources",
                ),
            ),
            nextgen=ApplicationFileManager(
                bucket_name=settings.NEXTGEN_S3_BUCKET_NAME,
                s3_client=s3_client.nextgen,
            ),
        ),
        jobscripts=db_gen(
            legacy=None,
            nextgen=FileManager(
                engine=EngineS3(s3_client.nextgen, settings.NEXTGEN_S3_BUCKET_NAME, "job-scripts"),
                transformation_list=LIST_OF_TRANSFORMATIONS,
                key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
            ),
        ),
    )

    return s3man


@contextlib.contextmanager
def get_upload_files_from_tar(s3_obj):

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with tarfile.open(fileobj=BytesIO(s3_obj), mode="r:gz") as tar:
            tar.extractall(tmp_path)

        with contextlib.ExitStack() as stack:
            yield [
                UploadFile(path.name, stack.enter_context(open(path)), "text/plain")
                for path in tmp_path.rglob("*")
                if path.is_file()
            ]


def transfer_s3(s3man, applications_map):
    """
    Transfer data from legacy s3 bucket to nextgen s3 bucket.

    If the application_id in the legacy s3 key name doesn't exist in our application
    map, skip the object. If the legacy s3 key doesn't match the expected pattern, skip
    the object. Otherwise put the object into the nextgen s3 bucket with the application
    id mapped to the appropriate nextgen application.
    """
    logger.info(
        f"Transferring S3 data from legacy to nextgen store, {len(applications_map)} applications are expected"
    )

    s3man.nextgen.source_files.engine.ensure_bucket()

    legacy_key_mapping = KeyMappingNumeratedFolder("jobbergate.tar.gz")

    bad_pattern_skips = 0
    missing_id_skips = 0
    error_when_uploading = 0
    successful_transfers = 0
    transferred_ids = []
    for legacy_key in s3man.legacy.keys():
        try:
            legacy_application_id = legacy_key_mapping.get_dict_key_from_engine(legacy_key)
        except (ValueError, TypeError):
            bad_pattern_skips += 1
            logger.warning(f"Bad pattern: {legacy_application_id=}")
            continue
        nextgen_application_id = applications_map.get(int(legacy_application_id))
        if not nextgen_application_id:
            missing_id_skips += 1
            logger.warning(f"Missing id: {legacy_application_id=}")
            continue

        legacy_obj = s3man.legacy[legacy_key]
        try:
            with get_upload_files_from_tar(legacy_obj) as upload_files:
                s3man.nextgen.write_to_s3(nextgen_application_id, upload_files, remove_previous_files=True)
        except Exception:
            error_when_uploading += 1
            logger.warning(f"Error when uploading the files: {legacy_application_id=}")
        else:
            transferred_ids.append(nextgen_application_id)
            successful_transfers += 1
            logger.trace(f"Successful transfer: {legacy_application_id=}")

    logger.info(f"Skipped {bad_pattern_skips} objects due to unparsable key")
    logger.info(
        f"Skipped {missing_id_skips} objects due to missing application_id (files on S3 but id not on nextgen database)"
    )
    logger.info(f"Skipped {error_when_uploading} unprocessable objects")
    logger.info(f"Finished transferring {successful_transfers} objects")

    return transferred_ids
