import pytest

from jobbergate_api.s3_manager import DummyClient, S3Manager


@pytest.mark.parametrize(
    "directory_name, desired_template",
    [
        ("applications", "applications/{app_id}/jobbergate.tar.gz"),
        ("job-script", "job-script/{app_id}/jobbergate.tar.gz"),
    ],
)
def test_s3_manager__key_template(directory_name, desired_template):
    s3man = S3Manager(directory_name=directory_name, client=DummyClient())
    assert s3man.key_template == desired_template
