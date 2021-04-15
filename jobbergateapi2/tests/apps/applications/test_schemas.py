"""
Test the schema of the resource Applcation
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.applications.schemas import Application


def test_create_application_missing_required_attribute(application_data):
    application_data.pop("application_name")

    with pytest.raises(ValidationError):
        Application(**application_data)


def test_application_string_conversion(application_data):
    application = Application(**application_data)

    assert str(application) == application_data.get("application_name")


@pytest.mark.freeze_time
def test_create_application(application_data):
    application = Application(created_at=datetime.utcnow(), **application_data)

    assert application.application_name == application_data["application_name"]
    assert application.application_file == application_data["application_file"]
    assert application.application_config == application_data["application_config"]
    assert application.created_at == datetime.utcnow()
