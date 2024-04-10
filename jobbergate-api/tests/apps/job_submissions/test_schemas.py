import pytest

from jobbergate_api.apps.job_submissions.schemas import JobSubmissionCreateRequest, JobSubmissionUpdateRequest


@pytest.mark.parametrize(
    "schema",
    [
        JobSubmissionCreateRequest(name="test", job_script_id=1, execution_directory=""),
        JobSubmissionUpdateRequest(execution_directory=""),
    ],
)
def test_empty_string_to_none(schema):
    """
    Assert that an empty string on execution_directory is converted to None.

    It was causing problems downstream since:
    >>> from pathlib import Path
    >>> Path("")
    PosixPath('.')

    With that, the default value was not applied on the Agent side.
    """
    assert schema.execution_directory is None
