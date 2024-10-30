from jobbergate_api.apps.job_submissions.tools import get_cloned_description
import pytest


@pytest.mark.parametrize(
    "description, expected_result",
    (
        ("", "[cloned from ID 123]"),
        ("test", "test [cloned from ID 123]"),
        ("test [cloned from ID 456]", "test [cloned from ID 123]"),
        ("[cloned from ID 456] test [cloned from ID 456]", "[cloned from ID 456] test [cloned from ID 123]"),
    ),
)
def test_get_cloned_description(description, expected_result):
    actual_result = get_cloned_description(description, 123)
    assert actual_result == expected_result
