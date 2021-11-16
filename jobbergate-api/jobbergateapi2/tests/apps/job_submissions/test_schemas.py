"""
Test the schema of the JobSubmission resource.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.job_submissions.schemas import JobSubmission


def test_create_job_submission_missing_required_attribute(job_submission_data):
    """
    Test that is not possible to create a JobSubmission without required attribute.
    """
    job_submission_data.pop("job_submission_name")

    with pytest.raises(ValidationError):
        JobSubmission(**job_submission_data)


def test_job_submission_string_conversion(job_submission_data):
    """
    Test the string representation of a JobSubmission object.
    """
    job_submission = JobSubmission(job_submission_owner_id=1, **job_submission_data)

    assert str(job_submission) == job_submission_data.get("job_submission_name")


@pytest.mark.freeze_time
def test_create_job_submission(job_submission_data):
    """
    Test the creation of a JobSubmission when the required attributes are present.
    """
    job_submission = JobSubmission(
        job_submission_owner_id="owner1", created_at=datetime.utcnow(), **job_submission_data
    )

    assert job_submission.job_submission_name == job_submission_data["job_submission_name"]
    assert job_submission.job_submission_owner_id == "owner1"
    assert job_submission.job_script_id == job_submission_data["job_script_id"]
    assert job_submission.created_at == datetime.utcnow()
