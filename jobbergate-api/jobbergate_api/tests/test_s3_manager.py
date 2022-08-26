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
    APPLICATION_SOURCE_FILE_NAME,
    APPLICATION_TEMPLATE_FOLDER,
    APPLICATIONS_WORK_DIR,
    ApplicationFiles,
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


def test_write_application_files_to_s3(
    make_dummy_file,
    make_uploaded_files,
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

    with make_uploaded_files(
        make_dummy_file("jobbergate.py", content=dummy_application_source_file),
        make_dummy_file("template-1.j2", content=dummy_template),
        make_dummy_file("template-2.jinja2", content=dummy_template),
        make_dummy_file("jobbergate.yaml", content=dummy_application_config),
    ) as uploaded_files:
        ApplicationFiles.get_from_upload_files(uploaded_files).write_to_s3(application_id)

    work_dir = mocked_file_manager_factory / APPLICATIONS_WORK_DIR / str(application_id)
    templates_dir = work_dir / APPLICATION_TEMPLATE_FOLDER

    application_path = work_dir / APPLICATION_SOURCE_FILE_NAME
    assert application_path.is_file()
    assert application_path.read_text() == dummy_application_source_file

    assert templates_dir.is_dir()

    template_path_1 = templates_dir / "template-1.j2"
    assert template_path_1.is_file()
    assert template_path_1.read_text() == dummy_template

    template_path_2 = templates_dir / "template-2.jinja2"
    assert template_path_2.is_file()
    assert template_path_2.read_text() == dummy_template


def test_get_application_files_from_s3(
    dummy_application_source_file,
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

    template_path_1 = templates_dir / "template-1.j2"
    template_path_1.write_text(dummy_template)

    template_path_2 = templates_dir / "template-2.jinja2"
    template_path_2.write_text(dummy_template)

    application_files = ApplicationFiles.get_from_s3(application_id)

    assert isinstance(application_files, ApplicationFiles)

    assert application_files.source_file == dummy_application_source_file

    assert application_files.templates == {
        "template-1.j2": dummy_template,
        "template-2.jinja2": dummy_template,
    }


def test_delete_application_files_from_s3(
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
