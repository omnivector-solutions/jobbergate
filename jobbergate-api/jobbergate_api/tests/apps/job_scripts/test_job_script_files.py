"""
Test job-script files.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from file_storehouse.engine import EngineLocal

from jobbergate_api.apps.job_scripts.job_script_files import (
    JOBSCRIPTS_MAIN_FILE_FOLDER,
    JOBSCRIPTS_SUPPORTING_FILES_FOLDER,
    JOBSCRIPTS_WORK_DIR,
    JobScriptFiles,
)


@pytest.fixture(scope="function")
def mocked_file_manager_factory(tmp_path):
    """
    Fixture to replace the default file engine (EngineS3) by a local one.

    In this way, all objects are stored in a temporary directory ``tmp_path``,
    that is yield for reference.
    """

    def local_engine_factory(*, work_directory: Path, **kwargs):
        return EngineLocal(base_path=tmp_path / work_directory)

    with patch("jobbergate_api.s3_manager.engine_factory", wraps=local_engine_factory):
        yield tmp_path


class TestJobScriptFiles:
    def test_check_main_file_path_is_in_files_keys__success(self):
        jobscript_files = JobScriptFiles(
            main_file_path="jobbergate.sh", files={"jobbergate.sh": "dummy-file-content"}
        )

        assert isinstance(jobscript_files, JobScriptFiles)

    def test_check_main_file_path_is_in_files_keys__error_main_file_path(self):
        with pytest.raises(ValueError):
            JobScriptFiles(
                main_file_path="wrong-filename",
                files={"jobbergate.sh": "dummy-file-content"},
            )

    def test_get_from_s3(self, mocked_file_manager_factory):

        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name
        main_file_path.parent.mkdir(parents=True, exist_ok=True)
        main_file_path.write_text(main_file_content)

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name
        supporting_file_path.parent.mkdir(parents=True, exist_ok=True)
        supporting_file_path.write_text(supporting_file_content)

        desired_jobscript_files = JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        )

        actual_jobscript_files = JobScriptFiles.get_from_s3(job_script_id)

        assert desired_jobscript_files == actual_jobscript_files

    def test_get_from_s3__no_main_file(self, mocked_file_manager_factory):
        job_script_id = 1
        with pytest.raises(
            ValueError,
            match="One main file is expected for a job-script, found 0",
        ):
            JobScriptFiles.get_from_s3(job_script_id)

    def test_delete_from_s3(self, mocked_file_manager_factory):

        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name
        main_file_path.parent.mkdir(parents=True, exist_ok=True)
        main_file_path.write_text(main_file_content)

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name
        supporting_file_path.parent.mkdir(parents=True, exist_ok=True)
        supporting_file_path.write_text(supporting_file_content)

        assert main_file_path.is_file()
        assert supporting_file_path.is_file()

        JobScriptFiles.delete_from_s3(job_script_id)

        assert not main_file_path.is_file()
        assert not supporting_file_path.is_file()

    def test_write_to_s3(self, mocked_file_manager_factory):

        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name

        JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        ).write_to_s3(job_script_id)

        assert main_file_path.is_file()
        assert main_file_path.read_text() == main_file_content

        assert supporting_file_path.is_file()
        assert supporting_file_path.read_text() == supporting_file_content

    def test_io_integration_with_s3(self, mocked_file_manager_factory):

        job_script_id = 1
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"

        actual_jobscript_files = JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        )

        actual_jobscript_files.write_to_s3(job_script_id)

        desired_jobscript_files = JobScriptFiles.get_from_s3(job_script_id)

        assert desired_jobscript_files == actual_jobscript_files

        JobScriptFiles.delete_from_s3(job_script_id)

        with pytest.raises(
            ValueError,
            match="One main file is expected for a job-script, found 0",
        ):
            JobScriptFiles.get_from_s3(job_script_id)
