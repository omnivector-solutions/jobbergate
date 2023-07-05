"""Test the router for the Job Script Template resource."""
import json

import pytest
from fastapi import status

from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateResponse
from jobbergate_api.apps.permissions import Permissions


@pytest.mark.asyncio
async def test_create_job_template__success(
    template_service, client, fill_job_template_data, inject_security_header, time_frame
):
    """Test a job template can be create."""
    assert (await template_service.count()) == 0

    payload = fill_job_template_data(
        identifier="create-template",
        template_vars={"foo": "bar"},
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    with time_frame() as window:
        response = await client.post("jobbergate/job-script-templates", json=payload)

    assert response.status_code == 201

    response_data = JobTemplateResponse(**response.json())

    assert response_data.name == payload["name"]
    assert response_data.description == payload["description"]
    assert response_data.identifier == payload["identifier"]
    assert response_data.template_vars == payload["template_vars"]
    assert response_data.owner_email == tester_email
    assert response_data.updated_at in window
    assert response_data.created_at in window
    assert response_data.template_files == {}
    assert response_data.workflow_file is None

    raw_db_data = await template_service.get(response_data.id)
    db_data = JobTemplateResponse.from_orm(raw_db_data)

    assert db_data == response_data

    assert (await template_service.count()) == 1


@pytest.mark.asyncio
async def test_create_job_template__fail_unauthorized(client, fill_job_template_data, template_service):
    """Test that the job template creation fails if the user is unauthorized."""
    assert (await template_service.count()) == 0

    payload = fill_job_template_data()
    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 401

    assert (await template_service.count()) == 0


@pytest.mark.asyncio
async def test_create_job_template__fail_identifier_already_exists(
    client, fill_job_template_data, template_service, inject_security_header
):
    """Test that the job template creation fails if the identifier already exists."""
    assert (await template_service.count()) == 0

    payload = fill_job_template_data(identifier="duplicated-template")

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 201
    assert (await template_service.count()) == 1

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 409
    assert (await template_service.count()) == 1


@pytest.mark.asyncio
async def test_create_job_template__fail_missing_name(
    client,
    fill_job_template_data,
    inject_security_header,
    template_service,
):
    """Test that the job template creation fails if a required field is missing."""
    assert (await template_service.count()) == 0

    payload = fill_job_template_data()

    payload.pop("name")

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    response = await client.post("jobbergate/job-script-templates", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    assert (await template_service.count()) == 0


@pytest.mark.asyncio
async def test_update_job_template__success(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    time_frame,
    template_service,
):
    raw_db_data = await template_service.create(**fill_job_template_data())
    await template_service.db_session.commit()
    original_data = JobTemplateResponse.from_orm(raw_db_data)

    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )

    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    with time_frame() as window:
        response = await client.put(f"jobbergate/job-script-templates/{original_data.id}", json=payload)

    assert response.status_code == 200

    response_data = JobTemplateResponse(**response.json())

    assert response_data.name == payload["name"]
    assert response_data.description == payload["description"]
    assert response_data.identifier == payload["identifier"]
    assert response_data.template_vars == payload["template_vars"]
    assert response_data.owner_email == tester_email
    assert response_data.updated_at in window
    assert response_data.template_files == {}
    assert response_data.workflow_file is None


@pytest.mark.asyncio
async def test_update_job_template__fail_not_found(
    client,
    tester_email,
    inject_security_header,
):
    job_template_id = 0
    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
    response = await client.put(f"jobbergate/job-script-templates/{job_template_id}", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_job_template__fail_unauthorized(client):
    job_template_id = 0
    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )
    response = await client.put(f"jobbergate/job-script-templates/{job_template_id}", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("identification_field", ("id", "identifier"))
async def test_get_job_template__success(
    identification_field,
    client,
    inject_security_header,
    fill_job_template_data,
):
    payload = fill_job_template_data(
        identifier=f"get-template-{identification_field}",
        template_vars={"foo": "bar"},
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    create_response = await client.post("jobbergate/job-script-templates", json=payload)
    create_response.raise_for_status()
    create_data = JobTemplateResponse(**create_response.json())

    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)

    identification = getattr(create_data, identification_field)
    response = await client.get(f"jobbergate/job-script-templates/{identification}")
    assert response.status_code == 200
    actual_data = JobTemplateResponse(**response.json())

    assert actual_data.name == payload["name"]
    assert actual_data.description == payload["description"]
    assert actual_data.identifier == payload["identifier"]
    assert actual_data.template_vars == payload["template_vars"]
    assert actual_data.owner_email == tester_email


@pytest.mark.asyncio
@pytest.mark.parametrize("identification_field", ("id", "identifier"))
async def test_delete_job_template__success(
    identification_field,
    client,
    tester_email,
    inject_security_header,
    fill_job_template_data,
):
    payload = fill_job_template_data(
        identifier=f"delete-template-{identification_field}",
        template_vars={"foo": "bar"},
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    response.raise_for_status()

    actual_data = JobTemplateResponse(**response.json())

    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
    identification = getattr(actual_data, identification_field)
    response = await client.delete(f"jobbergate/job-script-templates/{identification}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_job_template__fail_not_found(
    client,
    tester_email,
    inject_security_header,
):
    job_template_id = 0
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
    response = await client.delete(f"jobbergate/job-script-templates/{job_template_id}")
    assert response.status_code == 404


class TestListJobTemplates:
    """Test the list endpoint."""

    @pytest.mark.asyncio
    @pytest.fixture(scope="function")
    async def job_templates_list(self, template_service, fill_all_job_template_data):
        data = fill_all_job_template_data(
            {
                "name": "name-1",
                "description": "desc-1",
                "identifier": "identifier-1",
                "template_vars": {"foo-1": "bar-1"},
            },
            {
                "name": "name-2",
                "description": "desc-2",
                "identifier": "identifier-2",
                "template_vars": {"foo-1": "bar-2"},
            },
            {
                "name": "name-3",
                "description": "desc-3",
                "template_vars": {"foo-1": "bar-3"},
            },
            {
                "name": "name-4",
                "description": "desc-4",
                "template_vars": {"foo-1": "bar-4"},
                "owner_email": "test-test@pytest.com",
            },
        )
        for item in data:
            await template_service.create(**item)
        await template_service.db_session.commit()
        yield data

    @pytest.mark.asyncio
    async def test_list_job_templates__all_success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_templates_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get("jobbergate/job-script-templates?include_null_identifier=True")
        assert response.status_code == 200

        actual_data = response.json()
        assert actual_data["total"] == len(job_templates_list)
        assert actual_data["page"] == 1
        assert actual_data["size"] == 50
        assert actual_data["pages"] == 1

        for actual_item, expected_item in zip(actual_data["items"], job_templates_list):
            assert actual_item.get("identifier") == expected_item.get("identifier")
            assert actual_item["name"] == expected_item["name"]
            assert actual_item["description"] == expected_item["description"]
            assert actual_item["template_vars"] == expected_item["template_vars"]
            assert actual_item["owner_email"] == expected_item["owner_email"]
            assert actual_item["template_files"] == {}
            assert actual_item["workflow_file"] is None

    @pytest.mark.asyncio
    async def test_list_job_templates__user_only(
        self,
        client,
        tester_email,
        inject_security_header,
        job_templates_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(
            "jobbergate/job-script-templates?user_only=True&include_null_identifier=True"
        )
        assert response.status_code == 200

        actual_data = response.json()
        assert actual_data["total"] == 3

        expected_names = {i["name"] for i in job_templates_list if i["owner_email"] == tester_email}
        actual_names = {i["name"] for i in actual_data["items"]}

        assert expected_names == actual_names


class TestJobTemplateFiles:
    @pytest.fixture(scope="function")
    async def job_template_data(self, fill_job_template_data, template_service):
        raw_db_data = await template_service.create(**fill_job_template_data())
        await template_service.db_session.commit()
        yield JobTemplateResponse.from_orm(raw_db_data)

    @pytest.mark.asyncio
    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_template,
        make_dummy_file,
    ):
        id = job_template_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_template)

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as template_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/template/{file_type}",
                files={"upload_file": (dummy_file_path.name, template_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(f"jobbergate/job-script-templates/{id}")
        response.raise_for_status()

        actual_data = JobTemplateResponse.parse_obj(response.json())

        template_file_data = actual_data.template_files.get(dummy_file_path.name)

        assert template_file_data is not None
        assert template_file_data.file_type == file_type
        assert template_file_data.filename == dummy_file_path.name
        assert (
            template_file_data.path
            == f"/jobbergate/job-script-templates/{id}/upload/template/test_template.py.j2"
        )

        s3_object = await synth_bucket.Object(f"job_script_template_files/{id}/{dummy_file_path.name}")
        response = await s3_object.get()
        file_content = await response["Body"].read()
        assert dummy_template == file_content.decode()

    @pytest.mark.asyncio
    async def test_get__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        dummy_template,
        synth_bucket,
        make_dummy_file,
    ):
        id = job_template_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_template)

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as template_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/template/{file_type}",
                files={"upload_file": (dummy_file_path.name, template_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(
            f"jobbergate/job-script-templates/{id}/upload/template/{dummy_file_path.name}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == dummy_template

    @pytest.mark.asyncio
    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_template,
        make_dummy_file,
    ):
        id = job_template_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_template)

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as template_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/template/{file_type}",
                files={"upload_file": (dummy_file_path.name, template_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        response = await client.delete(
            f"jobbergate/job-script-templates/{id}/upload/template/{dummy_file_path.name}"
        )
        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(f"jobbergate/job-script-templates/{id}")
        response.raise_for_status()

        actual_data = JobTemplateResponse.parse_obj(response.json())

        assert dummy_file_path.name not in actual_data.template_files

        s3_object = await synth_bucket.Object(f"job_script_template_files/{id}/{dummy_file_path.name}")
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()


class TestJobTemplateWorkflowFile:
    @pytest.fixture(scope="function")
    async def job_template_data(self, fill_job_template_data, template_service):
        raw_db_data = await template_service.create(**fill_job_template_data())
        await template_service.db_session.commit()
        yield JobTemplateResponse.from_orm(raw_db_data)

    @pytest.mark.asyncio
    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_application_source_file,
        make_dummy_file,
    ):
        id = job_template_data.id
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_application_source_file)
        runtime_config = {"foo": "bar"}

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/workflow",
                files={"upload_file": (dummy_file_path.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(runtime_config)},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(f"jobbergate/job-script-templates/{id}")
        response.raise_for_status()

        actual_data = JobTemplateResponse.parse_obj(response.json())

        workflow_data = actual_data.workflow_file

        assert workflow_data is not None
        assert workflow_data.runtime_config == runtime_config
        assert workflow_data.path == f"/jobbergate/job-script-templates/{id}/upload/workflow"

        s3_object = await synth_bucket.Object(f"workflow_files/{id}/{WORKFLOW_FILE_NAME}")
        response = await s3_object.get()
        file_content = await response["Body"].read()
        assert dummy_application_source_file == file_content.decode()

    @pytest.mark.asyncio
    async def test_get__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_application_source_file,
        make_dummy_file,
    ):
        id = job_template_data.id
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_application_source_file)
        runtime_config = {"foo": "bar"}

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/workflow",
                files={"upload_file": (dummy_file_path.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(runtime_config)},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(f"jobbergate/job-script-templates/{id}/upload/workflow")

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == dummy_application_source_file

    @pytest.mark.asyncio
    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_application_source_file,
        make_dummy_file,
    ):
        id = job_template_data.id
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_application_source_file)
        runtime_config = {"foo": "bar"}

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        with open(dummy_file_path, mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{id}/upload/workflow",
                files={"upload_file": (dummy_file_path.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(runtime_config)},
            )

        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_EDIT)
        response = await client.delete(f"jobbergate/job-script-templates/{id}/upload/workflow")
        assert response.status_code == status.HTTP_200_OK

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_VIEW)
        response = await client.get(f"jobbergate/job-script-templates/{id}")
        response.raise_for_status()

        actual_data = JobTemplateResponse.parse_obj(response.json())

        assert actual_data.workflow_file is None

        s3_object = await synth_bucket.Object(f"workflow_files/{id}/{WORKFLOW_FILE_NAME}")
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()
