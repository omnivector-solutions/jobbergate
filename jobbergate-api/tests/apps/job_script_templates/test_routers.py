"""Test the router for the Job Script Template resource."""
import pytest

from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest, JobTemplateResponse
from jobbergate_api.apps.permissions import Permissions


@pytest.mark.asyncio
async def test_create_job_template__success(client, tester_email, inject_security_header):
    create_request = JobTemplateCreateRequest(
        name="Test Template",
        description="This is a test template",
        identifier="test-template",
        template_vars={"foo": "bar"},
    )
    inject_security_header(tester_email, Permissions.APPLICATIONS_EDIT)
    response = await client.post(
        "jobbergate/job-script-templates", json=create_request.dict(exclude_unset=True)
    )
    assert response.status_code == 201

    actual_data = JobTemplateResponse(**response.json())

    assert actual_data.name == create_request.name
    assert actual_data.description == create_request.description
    assert actual_data.identifier == create_request.identifier
    assert actual_data.template_vars == create_request.template_vars
    assert actual_data.owner_email == tester_email


@pytest.mark.asyncio
async def test_create_job_template__unauthorized(client):
    create_request = JobTemplateCreateRequest(
        name="Test Template",
        description="This is a test template",
        identifier="test-template",
        template_vars={"foo": "bar"},
    )
    response = await client.post(
        "jobbergate/job-script-templates", json=create_request.dict(exclude_unset=True)
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_job_template__success(
    client,
    tester_email,
    inject_security_header,
):
    create_request = JobTemplateCreateRequest(
        name="Test Template",
        description="This is a test template",
        identifier="test-delete-template",
        template_vars={"foo": "bar"},
    )
    inject_security_header(tester_email, Permissions.APPLICATIONS_EDIT)
    # response = await client.delete("jobbergate/job-script-templates/test-template")
    response = await client.post(
        "jobbergate/job-script-templates", json=create_request.dict(exclude_unset=True)
    )
    response.raise_for_status()

    actual_data = JobTemplateResponse(**response.json())

    inject_security_header(tester_email, Permissions.APPLICATIONS_EDIT)
    response = await client.delete(f"jobbergate/job-script-templates/{actual_data.id}")
    assert response.status_code == 204
