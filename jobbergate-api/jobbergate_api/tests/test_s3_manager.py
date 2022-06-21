import pytest
from fastapi.exceptions import HTTPException

from jobbergate_api.s3_manager import S3Manager, get_s3_object_as_tarfile, s3_client


@pytest.mark.parametrize(
    "directory_name, desired_template",
    [
        ("applications", "applications/{app_id}/jobbergate.tar.gz"),
        ("job-script", "job-script/{app_id}/jobbergate.tar.gz"),
    ],
)
def test_s3_manager__key_template(directory_name, desired_template):
    s3man = S3Manager(s3_client, directory_name, "jobbergate.tar.gz")
    assert s3man.key_template == desired_template


@pytest.fixture
def s3manager():
    return S3Manager(s3_client, "applications", "jobbergate.tar.gz")


@pytest.mark.parametrize(
    "key, id",
    [
        ("applications/0/jobbergate.tar.gz", "0"),
        ("applications/1/jobbergate.tar.gz", "1"),
        ("applications/2/jobbergate.tar.gz", "2"),
        ("applications/10/jobbergate.tar.gz", "10"),
        ("applications/100/jobbergate.tar.gz", "100"),
        ("applications/9999/jobbergate.tar.gz", "9999"),
    ],
)
class TestS3ManagerKeyIdTwoWayMapping:
    """
    A class to organize the parameters that test the conversions from
    id number to S3 key and vice versa, both performed by the S3 manager.
    """

    @pytest.mark.parametrize("input_type", [int, str])
    def test_s3_manager__get_key_from_id_str(self, s3manager, key, id, input_type):
        """
        Test the conversions from id number to S3 key.
        Notice both int and str are valid types for id and are tested.
        """
        assert s3manager._get_key_from_id(input_type(id)) == key

    def test_s3_manager__get_app_id_from_key(self, s3manager, key, id):
        """
        Test the conversions from S3 key to id number.
        """
        assert s3manager._get_app_id_from_key(key) == id


@pytest.fixture
def dummy_s3man(s3_object):
    """
    A dummy S3 manager used for tests containing only one key.
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
    Test exception when file not exists in S3 for get_s3_object function.
    """

    s3_file = None

    with pytest.raises(HTTPException) as exc:
        s3_file = get_s3_object_as_tarfile(dummy_s3man, 9999)

    assert "Application with id=9999 not found" in str(exc)

    assert s3_file is None
