from unittest import mock

import pytest
from botocore.exceptions import BotoCoreError
from fastapi.exceptions import HTTPException

from jobbergate_api.s3_manager import DummyClient, S3Client, S3Manager
from jobbergate_api.storage import database


@pytest.mark.parametrize(
    "directory_name, desired_template",
    [
        ("applications", "applications/{app_id}/jobbergate.tar.gz"),
        ("job-script", "job-script/{app_id}/jobbergate.tar.gz"),
    ],
)
def test_s3_manager__key_template(directory_name, desired_template):
    s3man = S3Manager(DummyClient(), directory_name)
    assert s3man.key_template == desired_template


s3man = S3Manager(S3Client(), "applications")


@pytest.mark.asyncio
@mock.patch.object(s3man.client, "s3_client")
@database.transaction(force_rollback=True)
async def test_get_s3_object_as_tarfile(s3man_client_mock, s3_object):
    """
    Test getting a file from S3 with get_s3_object function.
    """
    s3man_client_mock.get_object.return_value = s3_object

    s3_file = s3man.get_s3_object_as_tarfile(1)

    assert s3_file is not None
    s3man_client_mock.get_object.assert_called_once()


@mock.patch.object(s3man.client, "s3_client")
def test_get_s3_object_not_found(s3man_client_mock):
    """
    Test exception when file not exists in S3 for get_s3_object function.
    """
    s3man_client_mock.get_object.side_effect = BotoCoreError()

    s3_file = None
    with pytest.raises(HTTPException) as exc:
        s3_file = s3man.get_s3_object_as_tarfile(1)

    assert "Application with id=1 not found" in str(exc)

    assert s3_file is None
    s3man_client_mock.get_object.assert_called_once()
