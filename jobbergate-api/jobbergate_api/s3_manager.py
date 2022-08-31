"""
Provide a convenience class for managing calls to S3.
"""
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Tuple, Union

from boto3 import client
from botocore.client import BaseClient
from file_storehouse import (
    EngineS3,
    FileManager,
    FileManagerReadOnly,
    KeyMappingNumeratedFolder,
    TransformationABC,
    TransformationCodecs,
)
from loguru import logger
from pydantic import BaseModel, root_validator
from buzz import require_condition

from jobbergate_api.config import settings

JOBSCRIPTS_WORK_DIR = "job-scripts"
JOBSCRIPTS_MAIN_FILE_FOLDER = "main-file"
JOBSCRIPTS_SUPPORTING_FILES_FOLDER = "supporting-files"

IO_TRANSFORMATIONS = (TransformationCodecs("utf-8"),)
"""
Transformations to be performed when writing/reading S3 objects.

With this, all files are encoded/decoded with utf-8.

This constant can be shared between file managers.
"""


def engine_factory(*, s3_client: BaseClient, bucket_name: str, work_directory: Path) -> EngineS3:
    """
    Build an engine to manipulate objects from an s3 bucket.

    :param BaseClient s3_client: S3 client from boto3
    :param str bucket_name: The name of the s3 bucket
    :param Path work_directory: Work directory (referred as prefix at boto3 documentation)
    :return EngineS3: And engine to manipulate files from s3
    """
    return EngineS3(s3_client=s3_client, bucket_name=bucket_name, prefix=str(work_directory))


def file_manager_factory(
    id: int,
    *,
    s3_client: BaseClient,
    bucket_name: str,
    work_directory: Path,
    manager_cls: Union[FileManager, FileManagerReadOnly],
    transformations: Tuple[TransformationABC],
) -> Union[FileManager, FileManagerReadOnly]:
    """
    Build a file managers on demand.

    :param int id: identification number
    :param BaseClient s3_client: S3 client from boto3
    :param str bucket_name: The name of the s3 bucket
    :param Path work_directory: Work directory (referred as prefix at boto3 documentation)
    :param Union[FileManager, FileManagerReadOnly] manager_cls: Manager class (i/o access or just read only)
    :param Tuple[TransformationABC] transformations: I/o transformations
    :return Union[FileManager, FileManagerReadOnly]: Manager object
    """
    return manager_cls(
        engine=engine_factory(
            s3_client=s3_client,
            bucket_name=bucket_name,
            work_directory=work_directory / str(id),
        ),
        io_transformations=transformations,
    )


s3_client = client("s3", endpoint_url=settings.S3_ENDPOINT_URL)


s3man_jobscripts_factory: Callable[[int], FileManager] = partial(
    file_manager_factory,
    s3_client=s3_client,
    bucket_name=settings.S3_BUCKET_NAME,
    work_directory=Path(JOBSCRIPTS_WORK_DIR),
    manager_cls=FileManager,
    transformations=IO_TRANSFORMATIONS,
)


class JobScriptFiles(BaseModel):
    """
    Model containing job-script files.
    """

    main_file_path: Path
    files: Dict[Path, str]

    @root_validator(pre=False, skip_on_failure=True)
    def check_main_file_path_is_in_files_keys(cls, values):
        if values["main_file_path"] not in values["files"].keys():
            raise ValueError("main_file_path is not a valid key on the dict files")
        return values

    @classmethod
    def get_from_s3(cls, job_script_id: int):
        """
        Alternative method to initialize the model getting the objects from S3.
        """
        logger.debug(f"Getting job-script files from S3: {job_script_id=}")
        file_manager = s3man_jobscripts_factory(job_script_id)

        files = {}
        main_file_path = None
        main_file_counter = 0

        for s3_path in file_manager.keys():
            foldername = s3_path.parts[0]
            dict_path = s3_path.relative_to(foldername)
            if foldername == JOBSCRIPTS_MAIN_FILE_FOLDER:
                files[dict_path] = file_manager.get(s3_path)
                main_file_counter += 1
                main_file_path = dict_path
            elif foldername == JOBSCRIPTS_SUPPORTING_FILES_FOLDER:
                files[dict_path] = file_manager.get(s3_path)

        require_condition(
            main_file_counter == 1,
            f"One main file is expected for a job-script, found {main_file_counter}",
            ValueError,
        )

        return cls(main_file_path=main_file_path, files=files)

    @classmethod
    def delete_from_s3(cls, job_script_id: int):
        """
        Deleted the files associated with the given id.
        """
        logger.debug(f"Deleting from S3 the files associated to {job_script_id=}")
        file_manager = s3man_jobscripts_factory(job_script_id)
        file_manager.clear()
        logger.debug(f"Files were deleted for {job_script_id=}")

    def write_to_s3(self, job_script_id: int):
        logger.debug(f"Writing job-script files to S3: {job_script_id=}")

        file_manager = s3man_jobscripts_factory(job_script_id)

        for dict_path, content in self.files.items():
            if dict_path == self.main_file_path:
                s3_path = JOBSCRIPTS_MAIN_FILE_FOLDER / dict_path
            else:
                s3_path = JOBSCRIPTS_SUPPORTING_FILES_FOLDER / dict_path
            file_manager[s3_path] = content

        logger.debug("Done writing job-script files to S3")


s3man_jobscripts = FileManager(
    engine=EngineS3(s3_client, settings.S3_BUCKET_NAME, "job-scripts"),
    io_transformations=IO_TRANSFORMATIONS,
    key_mapping=KeyMappingNumeratedFolder("jobbergate.txt"),
)
