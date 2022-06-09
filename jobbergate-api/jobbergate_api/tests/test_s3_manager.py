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
