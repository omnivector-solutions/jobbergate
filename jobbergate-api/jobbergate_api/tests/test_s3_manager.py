"""
Test s3 manager.
"""

import contextlib
from unittest.mock import patch
from fastapi import UploadFile
from file_storehouse import FileManager, FileManagerReadOnly
import pytest
from fastapi.exceptions import HTTPException

from jobbergate_api.s3_manager import (
    application_template_manager_factory,
    delete_application_files_from_s3,
    get_s3_object_as_tarfile,
    s3man_applications_source_files,
    s3man_jobscripts,
    write_application_files_to_s3,
)


@pytest.mark.parametrize(
    "s3_manager, template",
    [
        (s3man_applications_source_files, "applications/{}/jobbergate.py"),
        (s3man_jobscripts, "job-scripts/{}/jobbergate.txt"),
    ],
)
@pytest.mark.parametrize("id", [0, 1, 2, 10, 100, 9999])
class TestS3ManagerKeyIdTwoWayMapping:
    """
    Test the conversions from id number to S3 key and vice versa.
    """

    @pytest.mark.parametrize("input_type", [int, str])
    def test_s3_manager__get_key_from_id_str(self, s3_manager, template, id, input_type):
        """
        Test the conversions from id number to S3 key.

        Notice both int and str are valid types for id and are tested.
        """
        key = template.format(id)
        assert s3_manager._get_engine_key(input_type(id)) == key

    def test_s3_manager__get_app_id_from_key(self, s3_manager, template, id):
        """
        Test the conversions from S3 key to id number.
        """
        key = template.format(id)
        assert s3_manager._get_dict_key(key) == id


@pytest.mark.parametrize(
    "ManagerClass, is_read_only",
    [
        (FileManager, False),
        (FileManagerReadOnly, True),
    ],
)
def test_application_template_manager_factory_returning_type(ManagerClass, is_read_only):
    """
    Test if the object returned by application_template_manager_factory is the expected.
    """
    assert isinstance(
        application_template_manager_factory(0, is_read_only=is_read_only),
        ManagerClass,
    )


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
                UploadFile(path.name, stack.enter_context(open(path)), "text/plain") for path in file_paths
            ]

    return _helper


@pytest.fixture(scope="function")
def mocked_application_template_manager():
    """
    Mock the template manager factory in order to make it return an empty dictionary.

    :yield dict: The dictionary representing the file manager.
    """
    mock_result_as_dict = {}
    with patch(
        "jobbergate_api.s3_manager.application_template_manager_factory",
        wraps=lambda *args, **kwargs: mock_result_as_dict,
    ):
        yield mock_result_as_dict
    mock_result_as_dict.clear()


@pytest.fixture(scope="function")
def mocked_applications_source_file_manager():
    """
    Mock the application source file manager in order to make it return an empty dictionary.

    :yield dict: The dictionary representing the file manager.
    """
    mock_result_as_dict = {}
    with patch("jobbergate_api.s3_manager.s3man_applications_source_files", mock_result_as_dict):
        yield mock_result_as_dict
    mock_result_as_dict.clear()


def test_write_application_files_to_s3(
    mocked_application_template_manager,
    mocked_applications_source_file_manager,
    make_dummy_file,
    make_uploaded_files,
    dummy_application_source_file,
    dummy_template,
    dummy_application_config,
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
        write_application_files_to_s3(application_id, uploaded_files, remove_previous_files=True)

    expected_templates = {"template-1.j2", "template-2.jinja2"}
    assert mocked_application_template_manager.keys() == expected_templates

    expected_source_files = {application_id}
    assert mocked_applications_source_file_manager.keys() == expected_source_files


def test_delete_application_files_from_s3(
    mocked_application_template_manager,
    mocked_applications_source_file_manager,
):
    """
    Test if the applications files are deleted from S3 as expected.

    To do so, test files are added to both file managers. Once one application id
    is deleted, all templated files related to it are deleted as well as its source
    file. Source files from any other id are expected to be preserved.
    """
    FILES_CONTENT = "test-file"

    mocked_applications_source_file_manager.update((i, FILES_CONTENT) for i in range(3))
    mocked_application_template_manager.update((f"{i}.j2", FILES_CONTENT) for i in range(3))

    delete_application_files_from_s3(application_id=1)

    assert mocked_applications_source_file_manager.keys() == {0, 2}
    assert len(mocked_application_template_manager) == 0


@pytest.fixture
def dummy_s3man(s3_object):
    """
    Provide a dummy S3 manager used for tests containing only one key and object.
    """
    return {1: s3_object}


@pytest.mark.asyncio
async def test_get_s3_object_as_tarfile(dummy_s3man):
    """
    Test getting a file from S3 with get_s3_object function.
    """
    s3_file = get_s3_object_as_tarfile(dummy_s3man, 1)

    assert s3_file is not None


@pytest.mark.asyncio
async def test_get_s3_object_not_found(dummy_s3man):
    """
    Test exception at get_s3_object function when file does not exist in S3.
    """
    s3_file = None

    with pytest.raises(HTTPException) as exc:
        s3_file = get_s3_object_as_tarfile(dummy_s3man, 9999)

    assert "Application with app_id=9999 not found in S3" in str(exc)

    assert s3_file is None
