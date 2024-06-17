import pytest
from pydantic import ValidationError

from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest


def test_not_empty_str__validator_not_applied_to_non_empty_strings():
    request = JobTemplateCreateRequest(name="test-name")

    assert request.name == "test-name"


def test_not_empty_str__validator_applied_to_empty_strings():
    with pytest.raises(ValidationError, match="Cannot be an empty string"):
        JobTemplateCreateRequest(name="")


def test_empty_str_to_none__validator_not_applied_to_non_empty_strings():
    request = JobTemplateCreateRequest(
        name="test-name",
        identifier="test-identifier",
    )

    assert request.identifier == "test-identifier"


def test_empty_str_to_none__validator_applied_to_empty_strings():
    request = JobTemplateCreateRequest(
        name="test-name",
        identifier="",
    )

    assert request.identifier is None
