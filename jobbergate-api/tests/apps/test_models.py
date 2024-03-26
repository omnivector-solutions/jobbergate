"""Test the the models."""

import pytest
from sqlalchemy import String

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.job_submissions.models import JobSubmission


@pytest.mark.parametrize("Model", (JobScriptTemplate, JobScript, JobSubmission))
def test_searchable_fields_are_strings(Model):
    """Test that the searchable fields are strings, so search will work."""
    assert all(isinstance(c.type, String) for c in Model.searchable_fields())
