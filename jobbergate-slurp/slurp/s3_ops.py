"""
Provides a convenience class for managing calls to S3.
"""
import contextlib
import json
import tarfile
import tempfile
from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import cast

from boto3 import client
from fastapi import UploadFile
from file_storehouse import FileManager, FileManagerReadOnly
from file_storehouse.engine.s3 import EngineS3
from file_storehouse.key_mapping import KeyMappingNumeratedFolder
from jobbergate_api.apps.applications.application_files import APPLICATIONS_WORK_DIR, ApplicationFiles
from jobbergate_api.apps.job_scripts.job_script_files import JOBSCRIPTS_WORK_DIR, JobScriptFiles
from jobbergate_api.s3_manager import IO_TRANSFORMATIONS, file_manager_factory
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

    class NextGenApplicationFiles(ApplicationFiles):
        @classmethod
        def file_manager_factory(self, application_id: int) -> FileManager:
            """
            Build an application file manager.
            """
            return cast(
                FileManager,
                file_manager_factory(
                    id=application_id,
                    s3_client=s3_client.nextgen,
                    bucket_name=settings.NEXTGEN_S3_BUCKET_NAME,
                    work_directory=Path(APPLICATIONS_WORK_DIR),
                    manager_cls=FileManager,
                    transformations=IO_TRANSFORMATIONS,
                ),
            )

    class NextGenJobScriptFiles(JobScriptFiles):
        @classmethod
        def file_manager_factory(self, job_script_id: int) -> FileManager:
            """
            Build an application file manager.
            """
            return cast(
                FileManager,
                file_manager_factory(
                    id=job_script_id,
                    s3_client=s3_client.nextgen,
                    bucket_name=settings.NEXTGEN_S3_BUCKET_NAME,
                    work_directory=Path(JOBSCRIPTS_WORK_DIR),
                    manager_cls=FileManager,
                    transformations=IO_TRANSFORMATIONS,
                ),
            )

        @classmethod
        def get_from_json(cls, input_json: dict):
            """
            Get job script files from the legacy json file ``job_script_data_as_string``.
            """
            main_filename = "application.sh"
            main_file_path = Path(main_filename)

            try:
                unpacked_data = json.loads(input_json)
                job_script = unpacked_data.get(main_filename, "")
            except json.JSONDecodeError:
                job_script = ""

            return cls(
                main_file_path=main_file_path,
                files={main_file_path: job_script},
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
            nextgen=NextGenApplicationFiles,
        ),
        jobscripts=db_gen(
            legacy=None,
            nextgen=NextGenJobScriptFiles,
        ),
    )

    return s3man


@contextlib.contextmanager
def get_upload_files_from_tar(s3_obj):

    supported_extensions = {".py", ".yaml", ".j2", ".jinja2"}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with tarfile.open(fileobj=BytesIO(s3_obj), mode="r:gz") as tar:
            tar.extractall(tmp_path)

        logger.debug(
            f"Extracted tarball to {tmp_path}, including the files: {[path.name for path in tmp_path.rglob('*')]}"
        )

        with contextlib.ExitStack() as stack:
            yield [
                UploadFile(
                    path.name,
                    stack.enter_context(open(path, "rb")),
                    "text/plain",
                )
                for path in tmp_path.rglob("*")
                if path.is_file() and path.suffix in supported_extensions
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
        "Transferring S3 data from legacy to nextgen store, "
        f"{len(applications_map)} applications are expected, "
        f"{len(s3man.legacy)} objects were found at the legacy bucket."
    )

    legacy_key_mapping = KeyMappingNumeratedFolder("jobbergate.tar.gz")

    bad_pattern_skips = 0
    missing_id_skips = 0
    error_when_uploading = 0
    successful_transfers = 0
    transferred_ids = []
    missing_files = set(applications_map.values())
    for legacy_key in s3man.legacy.keys():
        try:
            legacy_application_id = legacy_key_mapping.get_dict_key_from_engine(legacy_key)
        except (ValueError, TypeError):
            bad_pattern_skips += 1
            logger.warning(f"Bad pattern at legacy object {legacy_key.as_posix()}")
            continue
        nextgen_application_id = applications_map.get(int(legacy_application_id))
        if not nextgen_application_id:
            missing_id_skips += 1
            logger.warning(f"Missing id at legacy object {legacy_key.as_posix()}")
            continue

        legacy_obj = s3man.legacy[legacy_key]
        try:
            logger.debug(
                f"Started processing uploaded files {legacy_application_id=} "
                f"to {nextgen_application_id=} from the legacy bucket key '{str(legacy_key)}'"
            )
            with get_upload_files_from_tar(legacy_obj) as upload_files:
                application_files = s3man.nextgen.get_from_upload_files(upload_files)
        except Exception as e:
            error_when_uploading += 1
            logger.error(
                f"Error processing the files {legacy_application_id=} to {nextgen_application_id=}: {e}"
            )
        else:
            application_files.write_to_s3(nextgen_application_id, remove_previous_files=True)
            transferred_ids.append(nextgen_application_id)
            successful_transfers += 1
            missing_files.remove(nextgen_application_id)
            logger.debug(f"Successful transferred: {legacy_application_id=} to {nextgen_application_id=}")

    logger.info(
        f"Finished transferring {successful_transfers} objects from s3. "
        f"{len(applications_map)} applications were expected, "
        f"{len(s3man.legacy)} objects were found at the legacy bucket."
    )

    logger.info(f"Skipped {bad_pattern_skips} objects due to unparsable key on legacy bucket.")
    logger.info(
        f"Skipped {missing_id_skips} objects due to missing application_id (files on S3 but id not on nextgen database)"
    )
    logger.info(f"Skipped {error_when_uploading} unprocessable objects")
    logger.info(f"No application files were found for application ids: {missing_files}")

    return transferred_ids
