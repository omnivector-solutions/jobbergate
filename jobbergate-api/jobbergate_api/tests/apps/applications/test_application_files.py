"""
Test application files.
"""

import contextlib

import pytest
from fastapi import UploadFile

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.constants import (
    APPLICATION_CONFIG_FILE_NAME,
    APPLICATION_SOURCE_FILE_NAME,
    APPLICATION_TEMPLATE_FOLDER,
    APPLICATIONS_WORK_DIR,
)
from jobbergate_api.apps.applications.schemas import ApplicationConfig, JobbergateConfig


class TestApplicationConfig:
    """
    Test the application config base model.
    """

    def test_get_from_yaml_file_without_extra_params__success(self, dummy_application_config):
        """
        Test the model can be loaded from a yaml file without extra params.
        """
        desired_application_config = ApplicationConfig(
            application_config={"job_name": "rats", "partitions": ["debug", "partition1"]},
            jobbergate_config=JobbergateConfig(
                default_template="test_job_script.sh",
                supporting_files=["test_job_script.sh"],
                supporting_files_output_name={"test_job_script.sh": ["support_file_b.py"]},
                template_files=["templates/test_job_script.sh"],
                job_script_name=None,
                output_directory=".",
            ),
        )

        actual_application_config = ApplicationConfig.get_from_yaml_file(dummy_application_config)

        assert actual_application_config == desired_application_config

    def test_get_from_yaml_file_including_extra_params__success(self, dummy_application_config):
        """
        Test the model can be loaded from a yaml file with extra params.
        """
        user_supplied_parameters = dict(
            application_config=dict(job_name="testing"),
            jobbergate_config=dict(default_template="another_test_job_script.sh"),
        )

        desired_application_config = ApplicationConfig(
            application_config={"job_name": "testing"},
            jobbergate_config=JobbergateConfig(
                default_template="another_test_job_script.sh",
            ),
        )

        actual_application_config = ApplicationConfig.get_from_yaml_file(
            dummy_application_config, user_supplied_parameters
        )

        assert actual_application_config == desired_application_config

    def test_get_from_yaml_file_validation_error(self):
        """
        Test that ValueError is raised when the file does not have the necessary schema.
        """
        with pytest.raises(ValueError):
            ApplicationConfig.get_from_yaml_file("key: value")


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
    """
    Fixture to make a list of uploaded files.
    """
    with make_uploaded_files(
        make_dummy_file("jobbergate.py", content=dummy_application_source_file),
        make_dummy_file("template-1.j2", content=dummy_template),
        make_dummy_file("template-2.jinja2", content=dummy_template),
        make_dummy_file("jobbergate.yaml", content=dummy_application_config),
    ) as uploaded_files:
        yield uploaded_files


class TestApplicationFiles:
    """
    Test application files.
    """

    def test_get_application_files_from_upload_files(
        self,
        make_uploaded_files_filled,
        dummy_application_source_file,
        dummy_template,
        dummy_application_config,
    ):
        """
        Test that ApplicationFiles can be obtained from a list of uploaded files.
        """
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
        make_uploaded_files_filled,
        mocked_file_manager_factory,
    ):
        """
        Test that delete does not delete any file from any other application.
        """
        remaining_application_id = 1
        another_application_id = 2

        desired_application_files = ApplicationFiles.get_from_upload_files(
            make_uploaded_files_filled,
        )

        desired_application_files.write_to_s3(remaining_application_id)
        desired_application_files.write_to_s3(another_application_id)

        ApplicationFiles.delete_from_s3(another_application_id)

        deleted_application_files = ApplicationFiles.get_from_s3(another_application_id)
        assert deleted_application_files.dict(exclude_unset=True, exclude_defaults=True) == {"templates": {}}

        actual_application_files = ApplicationFiles.get_from_s3(remaining_application_id)
        assert desired_application_files == actual_application_files

    def test_complete_workflow(self, mocked_file_manager_factory, make_uploaded_files_filled):
        """
        End-to-end test, getting application files from uploaded files, than write/read them.
        """
        application_id = 1

        desired_application_files = ApplicationFiles.get_from_upload_files(
            make_uploaded_files_filled,
        )

        desired_application_files.write_to_s3(application_id)

        actual_application_files = ApplicationFiles.get_from_s3(application_id)

        assert desired_application_files == actual_application_files
