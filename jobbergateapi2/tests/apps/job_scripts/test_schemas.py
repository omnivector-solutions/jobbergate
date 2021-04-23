"""
Test the schema of the JobScript resource
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.job_scripts.schemas import JobScript


def test_create_job_script_missing_required_attribute(job_script_data):
    job_script_data.pop("job_script_name")

    with pytest.raises(ValidationError):
        JobScript(**job_script_data)


def test_job_script_string_conversion(job_script_data):
    job_script = JobScript(**job_script_data)

    assert str(job_script) == job_script_data.get("job_script_name")


@pytest.mark.freeze_time
def test_create_job_script(job_script_data):
    job_script = JobScript(created_at=datetime.utcnow(), **job_script_data)

    assert job_script.job_script_name == job_script_data["job_script_name"]
    assert job_script.job_script_data_as_string == job_script_data["job_script_data_as_string"]
    assert job_script.job_script_owner_id == job_script_data["job_script_owner_id"]
    assert job_script.application_id == job_script_data["application_id"]
    assert job_script.created_at == datetime.utcnow()
