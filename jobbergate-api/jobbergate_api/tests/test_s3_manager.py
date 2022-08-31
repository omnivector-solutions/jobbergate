"""
Test s3 manager.
"""

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest
from boto3 import client
from fastapi import UploadFile
from file_storehouse.engine import EngineLocal

from jobbergate_api.s3_manager import (
    APPLICATION_CONFIG_FILE_NAME,
    APPLICATION_SOURCE_FILE_NAME,
    APPLICATION_TEMPLATE_FOLDER,
    APPLICATIONS_WORK_DIR,
    JOBSCRIPTS_MAIN_FILE_FOLDER,
    JOBSCRIPTS_SUPPORTING_FILES_FOLDER,
    JOBSCRIPTS_WORK_DIR,
    ApplicationFiles,
    JobScriptFiles,
    engine_factory,
)


class TestEngineFactory:
    @pytest.fixture(scope="class")
    def client(self):
        return client("s3")

    @pytest.fixture(scope="class")
    def s3_engine(self, client):
        return engine_factory(
            s3_client=client,
            bucket_name="test-bucket",
            work_directory=Path("test-dir"),
        )

    def test_client(self, s3_engine, client):
        assert s3_engine.s3_client == client

    def test_bucket_name(self, s3_engine):
        assert s3_engine.bucket_name == "test-bucket"

    def test_prefix(self, s3_engine):
        assert s3_engine.prefix == "test-dir"


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


@pytest.fixture
def make_uploaded_files():
    """
    Provide a fixture to use as a context manager that builds a list of uploaded files.
    """

    @contextlib.contextmanager
    def _helper(*file_paths):
        """
        Context manager that opens the file(s) and yields the ``files`` param from it.
        """
        with contextlib.ExitStack() as stack:
            yield [
                UploadFile(path.name, stack.enter_context(open(path, "rb")), "text/plain")
                for path in file_paths
            ]

    return _helper


@pytest.fixture(scope="function")
def make_uploaded_files_filled(
    make_dummy_file,
    make_uploaded_files,
    dummy_application_source_file,
    dummy_template,
    dummy_application_config,
):
    with make_uploaded_files(
        make_dummy_file("jobbergate.py", content=dummy_application_source_file),
        make_dummy_file("template-1.j2", content=dummy_template),
        make_dummy_file("template-2.jinja2", content=dummy_template),
        make_dummy_file("jobbergate.yaml", content=dummy_application_config),
    ) as uploaded_files:
        yield uploaded_files


class TestApplicationFiles:
    def test_get_application_files_from_upload_files(
        self,
        make_uploaded_files_filled,
        dummy_application_source_file,
        dummy_template,
        dummy_application_config,
    ):

        application_files = ApplicationFiles.get_from_upload_files(make_uploaded_files_filled)

        assert isinstance(application_files, ApplicationFiles)

        assert application_files.config_file == dummy_application_config
        assert application_files.source_file == dummy_application_source_file
        assert application_files.templates == {
            "template-1.j2": dummy_template,
            "template-2.jinja2": dummy_template,
        }

    def test_write_application_files_to_s3(
        self,
        make_uploaded_files_filled,
        dummy_application_source_file,
        dummy_template,
        dummy_application_config,
        mocked_file_manager_factory,
    ):
        """
        Test if the applications files are written to S3 as expected.

        To do so, a list of uploaded files is created, than  we verify if each file
        went to the correct file manager.
        """
        application_id = 1

        ApplicationFiles.get_from_upload_files(
            make_uploaded_files_filled,
        ).write_to_s3(application_id)

        work_dir = mocked_file_manager_factory / APPLICATIONS_WORK_DIR / str(application_id)
        templates_dir = work_dir / APPLICATION_TEMPLATE_FOLDER

        application_source_path = work_dir / APPLICATION_SOURCE_FILE_NAME
        assert application_source_path.is_file()
        assert application_source_path.read_text() == dummy_application_source_file

        application_config_path = work_dir / APPLICATION_CONFIG_FILE_NAME
        assert application_config_path.is_file()
        assert application_config_path.read_text() == dummy_application_config

        assert templates_dir.is_dir()

        template_path_1 = templates_dir / "template-1.j2"
        assert template_path_1.is_file()
        assert template_path_1.read_text() == dummy_template

        template_path_2 = templates_dir / "template-2.jinja2"
        assert template_path_2.is_file()
        assert template_path_2.read_text() == dummy_template

    def test_get_application_files_from_s3(
        self,
        dummy_application_source_file,
        dummy_application_config,
        dummy_template,
        mocked_file_manager_factory,
    ):
        """
        Test if the application files are loaded from S3 as expected.

        To do so, dummy test files are added to the file managers and than loaded.
        """
        application_id = 1
        work_dir = mocked_file_manager_factory / APPLICATIONS_WORK_DIR / str(application_id)
        templates_dir = work_dir / APPLICATION_TEMPLATE_FOLDER
        templates_dir.mkdir(parents=True, exist_ok=True)

        application_path = work_dir / APPLICATION_SOURCE_FILE_NAME
        application_path.write_text(dummy_application_source_file)

        config_path = work_dir / APPLICATION_CONFIG_FILE_NAME
        config_path.write_text(dummy_application_config)

        template_path_1 = templates_dir / "template-1.j2"
        template_path_1.write_text(dummy_template)

        template_path_2 = templates_dir / "template-2.jinja2"
        template_path_2.write_text(dummy_template)

        application_files = ApplicationFiles.get_from_s3(application_id)

        assert isinstance(application_files, ApplicationFiles)

        assert application_files.source_file == dummy_application_source_file

        assert application_files.config_file == dummy_application_config

        assert application_files.templates == {
            "template-1.j2": dummy_template,
            "template-2.jinja2": dummy_template,
        }

    def test_delete_application_files_from_s3(
        self,
        dummy_application_source_file,
        dummy_template,
        mocked_file_manager_factory,
    ):
        """
        Test if the applications files are deleted from S3 as expected.

        To do so, test files are added to both file managers. Once one application id
        is deleted, all templated files related to it are deleted as well as its source
        file. Source files from any other id are expected to be preserved.
        """
        application_id = 1

        work_dir = mocked_file_manager_factory / APPLICATIONS_WORK_DIR / str(application_id)
        templates_dir = work_dir / APPLICATION_TEMPLATE_FOLDER
        templates_dir.mkdir(parents=True, exist_ok=True)

        application_path = work_dir / APPLICATION_SOURCE_FILE_NAME
        application_path.write_text(dummy_application_source_file)

        template_path_1 = templates_dir / "template-1.j2"
        template_path_1.write_text(dummy_template)

        template_path_2 = templates_dir / "template-2.jinja2"
        template_path_2.write_text(dummy_template)

        ApplicationFiles.delete_from_s3(application_id)

        assert not application_path.is_file()
        assert not template_path_1.is_file()
        assert not template_path_2.is_file()

    def test_delete_just_act_on_one_id(
        self,
        mocked_file_manager_factory,
        make_uploaded_files_filled,
    ):
        remaining_application_id = 1
        another_application_id = 2

        desired_application_files = ApplicationFiles.get_from_upload_files(
            make_uploaded_files_filled,
        )

        desired_application_files.write_to_s3(remaining_application_id)
        desired_application_files.write_to_s3(another_application_id)

        ApplicationFiles.delete_from_s3(another_application_id)

        deleted_application_files = ApplicationFiles.get_from_s3(another_application_id)
        assert deleted_application_files.dict(exclude_unset=True, exclude_defaults=True) == {}

        actual_application_files = ApplicationFiles.get_from_s3(remaining_application_id)
        assert desired_application_files == actual_application_files

    def test_complete_workflow(self, mocked_file_manager_factory, make_uploaded_files_filled):
        application_id = 1

        desired_application_files = ApplicationFiles.get_from_upload_files(
            make_uploaded_files_filled,
        )

        desired_application_files.write_to_s3(application_id)

        actual_application_files = ApplicationFiles.get_from_s3(application_id)

        assert desired_application_files == actual_application_files


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
