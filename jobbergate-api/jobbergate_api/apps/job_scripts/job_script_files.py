"""
Provide a convenience class for managing job-script files.
"""

from functools import partial
from pathlib import Path
from typing import Callable, Dict

from buzz import require_condition
from file_storehouse import FileManager
from loguru import logger
from pydantic import BaseModel, root_validator

from jobbergate_api.config import settings
from jobbergate_api.s3_manager import IO_TRANSFORMATIONS, file_manager_factory, s3_client

JOBSCRIPTS_WORK_DIR = "job-scripts"
JOBSCRIPTS_MAIN_FILE_FOLDER = "main-file"
JOBSCRIPTS_SUPPORTING_FILES_FOLDER = "supporting-files"

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
