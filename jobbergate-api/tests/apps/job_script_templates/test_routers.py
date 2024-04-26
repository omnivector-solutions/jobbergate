"""Test the router for the Job Script Template resource."""

import json

import pytest
from fastapi import status

from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateDetailedView, JobTemplateListView
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.services import ServiceError

# Not using the synth_session fixture in a route that needs the database is unsafe
pytest.mark.usefixtures("synth_session")


async def test_create_job_template__success(
    client,
    fill_job_template_data,
    inject_security_header,
    synth_services,
):
    """Test a job template can be created."""
    payload = fill_job_template_data(
        identifier="create-template",
        name="Test Template",
        description="This is a test template",
        template_vars=dict(foo="bar"),
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 201, f"Create failed: {response.text}"
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["identifier"] == payload["identifier"]
    assert response_data["template_vars"] == payload["template_vars"]
    assert response_data["owner_email"] == tester_email
    assert response_data["template_files"] is None
    assert response_data["workflow_files"] is None

    # Make sure the data was actually inserted into the database
    assert (await synth_services.crud.template.count()) == 1
    instance = await synth_services.crud.template.get(response_data["id"])
    assert instance is not None
    assert instance.identifier == "create-template"
    assert instance.name == "Test Template"
    assert instance.description == "This is a test template"
    assert instance.template_vars == dict(foo="bar")

    # Make sure that the data can be retrieved with a GET request
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
    response = await client.get(f"jobbergate/job-script-templates/{instance.id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["identifier"] == "create-template"
    assert response_data["name"] == "Test Template"
    assert response_data["description"] == "This is a test template"
    assert response_data["template_vars"] == dict(foo="bar")


async def test_create_job_template__fails_if_name_is_empty(
    client,
    fill_job_template_data,
    inject_security_header,
    synth_services,
):
    payload = fill_job_template_data(
        identifier="create-template",
        name="",
        description="This is a test template",
        template_vars=dict(foo="bar"),
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 422
    assert "Cannot be an empty string" in response.text
    assert (await synth_services.crud.template.count()) == 0


async def test_create_job_template__coerces_empty_identifier_to_None(
    client,
    fill_job_template_data,
    inject_security_header,
    synth_services,
):
    payload = fill_job_template_data(
        identifier="",
        name="Test Template",
        description="This is a test template",
        template_vars=dict(foo="bar"),
    )

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 201, f"Create failed: {response.text}"
    response_data = response.json()

    assert response_data["identifier"] == None


async def test_create_job_template__fail_unauthorized(client, fill_job_template_data, synth_services):
    """Test that the job template creation fails if the user is unauthorized."""
    payload = fill_job_template_data()
    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 401
    assert (await synth_services.crud.template.count()) == 0


async def test_create_job_template__fail_identifier_already_exists(
    client,
    fill_job_template_data,
    inject_security_header,
    synth_services,
):
    """Test that the job template creation fails if the identifier already exists."""
    payload = fill_job_template_data(identifier="duplicated-template")

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 201
    assert (await synth_services.crud.template.count()) == 1

    response = await client.post("jobbergate/job-script-templates", json=payload)
    assert response.status_code == 409
    assert (await synth_services.crud.template.count()) == 1


async def test_create_job_template__fail_missing_name(
    client,
    fill_job_template_data,
    inject_security_header,
    synth_services,
):
    """Test that the job template creation fails if a required field is missing."""
    payload = fill_job_template_data()

    payload.pop("name")

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)

    response = await client.post("jobbergate/job-script-templates", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    assert (await synth_services.crud.template.count()) == 0


@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_TEMPLATES_UPDATE]),
        (False, [Permissions.JOB_TEMPLATES_UPDATE, Permissions.ADMIN]),
    ],
)
async def test_update_job_template__success(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    synth_services,
    is_owner,
    permissions,
):
    instance = await synth_services.crud.template.create(**fill_job_template_data())

    requester_email = tester_email if is_owner else "another_" + tester_email

    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )

    inject_security_header(requester_email, *permissions)
    response = await client.put(
        f"jobbergate/job-script-templates/{instance.id}",
        json=payload,
    )

    assert response.status_code == 200, f"Update failed: {response.text}"
    response_data = response.json()
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["identifier"] == payload["identifier"]
    assert response_data["template_vars"] == payload["template_vars"]


async def test_update_job_template__fail_not_found(
    client,
    tester_email,
    inject_security_header,
    synth_session,
):
    job_template_id = 0
    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_UPDATE)
    response = await client.put(f"jobbergate/job-script-templates/{job_template_id}", json=payload)
    assert response.status_code == 404


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


async def test_update_job_template__forbidden(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    instance = await synth_services.crud.template.create(**fill_job_template_data())

    owner_email = tester_email
    requester_email = "another_" + owner_email

    payload = dict(
        name="new-name",
        identifier="new-identifier",
        description="new-description",
        template_vars={"new": "value"},
    )

    inject_security_header(requester_email, Permissions.JOB_TEMPLATES_UPDATE)
    response = await client.put(
        f"jobbergate/job-script-templates/{instance.id}",
        json=payload,
    )

    assert response.status_code == 403


@pytest.mark.parametrize("identification_field", ("id", "identifier"))
async def test_get_job_template__success(
    identification_field,
    client,
    inject_security_header,
    fill_job_template_data,
    synth_services,
):
    payload = fill_job_template_data(
        identifier=f"get-template-{identification_field}",
        template_vars={"foo": "bar"},
    )
    instance = await synth_services.crud.template.create(**payload)

    identification = getattr(instance, identification_field)

    inject_security_header(instance.owner_email, Permissions.JOB_TEMPLATES_READ)
    response = await client.get(f"jobbergate/job-script-templates/{identification}")
    assert response.status_code == 200, f"Get failed: {response.text}"
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["identifier"] == payload["identifier"]
    assert response_data["template_vars"] == payload["template_vars"]
    assert response_data["owner_email"] == payload["owner_email"]


@pytest.mark.parametrize("identification_field", ("id", "identifier"))
@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_TEMPLATES_DELETE]),
        (False, [Permissions.JOB_TEMPLATES_DELETE, Permissions.ADMIN]),
    ],
)
async def test_delete_job_template__success(
    identification_field,
    client,
    tester_email,
    inject_security_header,
    fill_job_template_data,
    synth_services,
    is_owner,
    permissions,
):
    payload = fill_job_template_data(
        identifier=f"delete-template-{identification_field}",
        template_vars={"foo": "bar"},
    )
    instance = await synth_services.crud.template.create(**payload)

    requester_email = tester_email if is_owner else "another_" + tester_email

    inject_security_header(requester_email, *permissions)
    identification = getattr(instance, identification_field)
    response = await client.delete(f"jobbergate/job-script-templates/{identification}")
    assert response.status_code == 204, f"Delete failed: {response.text}"

    assert (await synth_services.crud.template.count()) == 0


async def test_delete_job_template__fail_not_found(
    client,
    tester_email,
    inject_security_header,
    synth_session,
):
    job_template_id = 0
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_DELETE)
    response = await client.delete(f"jobbergate/job-script-templates/{job_template_id}")
    assert response.status_code == 404


@pytest.mark.parametrize("identification_field", ("id", "identifier"))
async def test_delete_job_template__forbidden(
    identification_field,
    client,
    tester_email,
    inject_security_header,
    fill_job_template_data,
    synth_services,
):
    owner_email = tester_email
    requester_email = "another_" + owner_email

    payload = fill_job_template_data(
        identifier=f"delete-template-forbidden-{identification_field}",
        template_vars={"foo": "bar"},
    )
    instance = await synth_services.crud.template.create(**payload)

    inject_security_header(requester_email, Permissions.JOB_TEMPLATES_DELETE)
    identification = getattr(instance, identification_field)
    response = await client.delete(f"jobbergate/job-script-templates/{identification}")
    assert response.status_code == 403

    assert (await synth_services.crud.template.count()) == 1


async def test_clone_job_template__success(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    original_instance = await synth_services.crud.template.create(
        **fill_job_template_data(owner_email=tester_email, identifier="test-identifier")
    )
    parent_id = original_instance.id
    await synth_services.file.template.upsert(
        parent_id=parent_id,
        filename="test_template.py.j2",
        upload_content="print('dummy file data')",
        file_type="ENTRYPOINT",
    )
    await synth_services.file.template.upsert(
        parent_id=parent_id,
        filename="test_template.j2",
        upload_content="support dummy file data",
        file_type="SUPPORT",
    )
    await synth_services.file.workflow.upsert(
        parent_id=parent_id,
        filename="jobbergate.py",
        upload_content="print('dummy file data')",
    )

    new_owner_email = "new_" + tester_email

    inject_security_header(new_owner_email, Permissions.JOB_TEMPLATES_CREATE)
    response = await client.post(f"jobbergate/job-script-templates/clone/{original_instance.id}")

    assert response.status_code == 201, f"Clone failed: {response.text}"
    response_data = response.json()

    cloned_id = response_data["id"]

    assert cloned_id != original_instance.id
    assert response_data["name"] == original_instance.name
    assert response_data["description"] == original_instance.description
    assert response_data["identifier"] is None
    assert response_data["template_vars"] == original_instance.template_vars
    assert response_data["owner_email"] == new_owner_email
    assert response_data["cloned_from_id"] == original_instance.id

    assert {f["filename"] for f in response_data["template_files"]} == {
        "test_template.py.j2",
        "test_template.j2",
    }
    assert {f["filename"] for f in response_data["workflow_files"]} == {"jobbergate.py"}


async def test_clone_job_template__replace_base_values(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    original_instance = await synth_services.crud.template.create(
        **fill_job_template_data(owner_email=tester_email, identifier="test-identifier")
    )

    new_owner_email = "new_" + tester_email

    payload = dict(
        name="new_name",
        description="new_description",
        identifier="new_identifier",
        template_vars={"new": "value"},
    )

    inject_security_header(new_owner_email, Permissions.JOB_TEMPLATES_CREATE)
    response = await client.post(
        f"jobbergate/job-script-templates/clone/{original_instance.id}", json=payload
    )

    assert response.status_code == 201, f"Clone failed: {response.text}"
    response_data = response.json()
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["identifier"] == payload["identifier"]
    assert response_data["template_vars"] == payload["template_vars"]
    assert response_data["owner_email"] == new_owner_email
    assert response_data["cloned_from_id"] == original_instance.id


async def test_clone_job_template__fail_unauthorized(
    client,
    fill_job_template_data,
    synth_services,
):
    original_instance = await synth_services.crud.template.create(**fill_job_template_data())

    response = await client.post(f"jobbergate/job-script-templates/clone/{original_instance.id}")

    assert response.status_code == 401


async def test_clone_job_template__fail_not_found(
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    assert (await synth_services.crud.template.count()) == 0
    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)
    response = await client.post("jobbergate/job-script-templates/clone/0")

    assert response.status_code == 404


async def test_clone_job_template__fail_conflict(
    client,
    fill_job_template_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    identifier = "test-identifier"
    original_instance = await synth_services.crud.template.create(
        **fill_job_template_data(owner_email=tester_email, identifier=identifier)
    )

    inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)
    response = await client.post(
        f"jobbergate/job-script-templates/clone/{original_instance.id}", json=dict(identifier=identifier)
    )

    assert response.status_code == 409


class TestListJobTemplates:
    """Test the list endpoint."""

    @pytest.fixture(scope="function")
    async def job_templates_list(self, synth_services, fill_all_job_template_data):
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
            {
                "name": "name-5",
                "description": "desc-5",
                "template_vars": {"foo-1": "bar-5"},
                "is_archived": True,
            },
        )
        for item in data:
            await synth_services.crud.template.create(**item)
        yield data

    async def test_list_job_templates__all_success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_templates_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(
            "jobbergate/job-script-templates",
            params=dict(include_null_identifier=True, include_archived=True, sort_field="id"),
        )
        assert response.status_code == 200, f"List failed: {response.text}"

        response_data = response.json()
        assert response_data["total"] == len(job_templates_list)
        assert response_data["page"] == 1
        assert response_data["size"] == 50
        assert response_data["pages"] == 1

        for response_item, expected_item in zip(response_data["items"], job_templates_list):
            assert response_item.get("identifier") == expected_item.get("identifier")
            assert response_item["name"] == expected_item["name"]
            assert response_item["description"] == expected_item["description"]
            assert response_item["owner_email"] == expected_item["owner_email"]
            assert response_item["is_archived"] == expected_item["is_archived"]

    async def test_list_job_templates__ignore_archived(
        self,
        client,
        tester_email,
        inject_security_header,
        job_templates_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get("jobbergate/job-script-templates?include_null_identifier=True")
        assert response.status_code == 200, f"List failed: {response.text}"

        response_data = response.json()

        expected_names = {i["name"] for i in job_templates_list if i["is_archived"] is False}
        response_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == response_names

    async def test_list_job_templates__user_only(
        self,
        client,
        tester_email,
        inject_security_header,
        job_templates_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(
            "jobbergate/job-script-templates?user_only=True&include_null_identifier=True&include_archived=True"
        )
        assert response.status_code == 200, f"List failed: {response.text}"

        response_data = response.json()

        expected_names = {i["name"] for i in job_templates_list if i["owner_email"] == tester_email}
        response_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == response_names


class TestJobTemplateFiles:
    @pytest.fixture(scope="function")
    async def job_template_data(self, fill_job_template_data, synth_services):
        raw_db_data = await synth_services.crud.template.create(**fill_job_template_data())
        yield JobTemplateDetailedView.from_orm(raw_db_data)

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_CREATE]),
            (False, [Permissions.JOB_TEMPLATES_CREATE, Permissions.ADMIN]),
        ],
    )
    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_template,
        make_dummy_file,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_template)

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        with open(dummy_file_path, mode="rb") as template_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/template/{file_type}",
                files={"upload_file": (dummy_file_path.name, template_file, "text/plain")},
            )

        # First, check the response from the upload endpoint
        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"
        response_data = response.json()
        assert response_data is not None
        assert response_data["parent_id"] == parent_id
        assert response_data["filename"] == dummy_file_path.name
        assert response_data["file_type"] == file_type

        # Next, check that the object was inserted into the s3 bucket
        s3_object = await synth_bucket.Object(f"job_script_template_files/{parent_id}/{dummy_file_path.name}")
        response = await s3_object.get()
        file_content = await response["Body"].read()
        assert dummy_template == file_content.decode()

        # Finally, see that the file is included in the parent template file list
        inject_security_header(requester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(f"jobbergate/job-script-templates/{parent_id}")
        assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"

        response_data = response.json()

        template_files = response_data["template_files"]
        assert len(template_files) == 1
        template_file = template_files.pop()
        assert template_file["parent_id"] == parent_id
        assert template_file["filename"] == dummy_file_path.name
        assert template_file["file_type"] == file_type

    async def test_create__fail_forbidden(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        dummy_template,
        make_dummy_file,
    ):
        parent_id = job_template_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_template)

        owner_email = tester_email
        requester_email = "another_" + owner_email

        inject_security_header(requester_email, Permissions.JOB_TEMPLATES_CREATE)
        with open(dummy_file_path, mode="rb") as template_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/template/{file_type}",
                files={"upload_file": (dummy_file_path.name, template_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_get__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_services,
    ):
        parent_id = job_template_data.id
        await synth_services.file.template.upsert(
            parent_id=parent_id,
            filename="test_template.py.j2",
            upload_content="dummy file data",
            file_type="ENTRYPOINT",
        )

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(
            f"jobbergate/job-script-templates/{job_template_data.id}/upload/template/test_template.py.j2"
        )

        assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"
        assert response.content.decode() == "dummy file data"

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_DELETE]),
            (False, [Permissions.JOB_TEMPLATES_DELETE, Permissions.ADMIN]),
        ],
    )
    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        synth_services,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        await synth_services.file.template.upsert(
            parent_id=parent_id,
            filename="test_template.py.j2",
            upload_content="dummy file data",
            file_type="ENTRYPOINT",
        )

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        response = await client.delete(
            f"jobbergate/job-script-templates/{parent_id}/upload/template/test_template.py.j2"
        )
        assert response.status_code == status.HTTP_200_OK, f"Delete failed: {response.text}"

        s3_object = await synth_bucket.Object(f"job_script_template_files/{parent_id}/test_template.py.j2")
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()

    async def test_delete__fail_forbidden(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_services,
    ):
        parent_id = job_template_data.id
        await synth_services.file.template.upsert(
            parent_id=parent_id,
            filename="test_template.py.j2",
            upload_content="dummy file data",
            file_type="ENTRYPOINT",
        )

        owner_email = tester_email
        requester_email = "another_" + owner_email

        inject_security_header(requester_email, Permissions.JOB_TEMPLATES_DELETE)
        response = await client.delete(
            f"jobbergate/job-script-templates/{parent_id}/upload/template/test_template.py.j2"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestJobTemplateWorkflowFile:
    @pytest.fixture(scope="function")
    async def job_template_data(self, fill_job_template_data, synth_services):
        raw_db_data = await synth_services.crud.template.create(**fill_job_template_data())
        yield JobTemplateListView.from_orm(raw_db_data)

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_CREATE]),
            (False, [Permissions.JOB_TEMPLATES_CREATE, Permissions.ADMIN]),
        ],
    )
    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        dummy_application_source_file,
        make_dummy_file,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_application_source_file)
        runtime_config = {"foo": "bar"}

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        with open(dummy_file_path, mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/workflow",
                files={"upload_file": (dummy_file_path.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(runtime_config)},
            )

        # First, check the response from the upload endpoint
        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"
        response_data = response.json()
        assert response_data is not None
        assert response_data["parent_id"] == parent_id
        assert response_data["filename"] == WORKFLOW_FILE_NAME
        assert response_data["runtime_config"] == runtime_config

        # Next, check that the object was inserted into the s3 bucket
        s3_object = await synth_bucket.Object(f"workflow_files/{parent_id}/{WORKFLOW_FILE_NAME}")
        response = await s3_object.get()
        file_content = await response["Body"].read()
        assert dummy_application_source_file == file_content.decode()

        # Finally, see that the file is included in the parent template file list
        inject_security_header(requester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(f"jobbergate/job-script-templates/{parent_id}")
        assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"

        response_data = response.json()

        workflow_files = response_data["workflow_files"]
        assert len(workflow_files) == 1
        workflow_file = workflow_files.pop()
        assert workflow_file["parent_id"] == parent_id
        assert workflow_file["filename"] == WORKFLOW_FILE_NAME
        assert workflow_file["runtime_config"] == runtime_config

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_CREATE]),
            (False, [Permissions.JOB_TEMPLATES_CREATE, Permissions.ADMIN]),
        ],
    )
    async def test_update__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_services,
        make_dummy_file,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        original_runtime_config = {"foo": "bar"}
        original_content = "import this"

        await synth_services.file.workflow.upsert(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
            upload_content=original_content,
            runtime_config=original_runtime_config,
        )

        new_runtime_config = {"new": "config"}
        new_content = "import that"

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        with open(make_dummy_file("test_template.py.j2", content=new_content), mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/workflow",
                files={"upload_file": (workflow_file.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(new_runtime_config)},
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        workflow_file = await synth_services.file.workflow.get(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
        )

        assert workflow_file.runtime_config == new_runtime_config
        assert (await synth_services.file.workflow.get_file_content(workflow_file)) == new_content.encode()

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_CREATE]),
            (False, [Permissions.JOB_TEMPLATES_CREATE, Permissions.ADMIN]),
        ],
    )
    async def test_update_optional_runtime_config__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_services,
        make_dummy_file,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        original_runtime_config = {"foo": "bar"}
        original_content = "import this"

        await synth_services.file.workflow.upsert(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
            upload_content=original_content,
            runtime_config=original_runtime_config,
        )

        new_content = "import that"

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        with open(make_dummy_file("test_template.py.j2", content=new_content), mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/workflow",
                files={"upload_file": (workflow_file.name, workflow_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        workflow_file = await synth_services.file.workflow.get(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
        )

        assert workflow_file.runtime_config == original_runtime_config
        assert (await synth_services.file.workflow.get_file_content(workflow_file)) == new_content.encode()

    async def test_update_optional_runtime_config__fail_on_creation_time(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_services,
        make_dummy_file,
    ):
        parent_id = job_template_data.id

        new_content = "import that"

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_CREATE)
        with open(make_dummy_file("test_template.py.j2", content=new_content), mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/workflow",
                files={"upload_file": (workflow_file.name, workflow_file, "text/plain")},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            response.json()["detail"]
            == "Runtime configuration is required when the workflow file does not exist"
        )

        with pytest.raises(ServiceError, match="workflow_files row not found"):
            await synth_services.file.workflow.get(parent_id=parent_id, filename=WORKFLOW_FILE_NAME)

    async def test_create__fail_forbidden(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        dummy_application_source_file,
        make_dummy_file,
    ):
        parent_id = job_template_data.id
        dummy_file_path = make_dummy_file("test_template.py.j2", content=dummy_application_source_file)
        runtime_config = {"foo": "bar"}

        owner_email = tester_email
        requester_email = "another_" + owner_email

        inject_security_header(requester_email, Permissions.JOB_TEMPLATES_CREATE)
        with open(dummy_file_path, mode="rb") as workflow_file:
            response = await client.put(
                f"jobbergate/job-script-templates/{parent_id}/upload/workflow",
                files={"upload_file": (dummy_file_path.name, workflow_file, "text/plain")},
                data={"runtime_config": json.dumps(runtime_config)},
            )

        # First, check the response from the upload endpoint
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_get__success(
        self, client, tester_email, inject_security_header, job_template_data, synth_services
    ):
        parent_id = job_template_data.id
        await synth_services.file.workflow.upsert(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
            upload_content="import this",
            runtime_config=dict(foo="bar"),
        )

        inject_security_header(tester_email, Permissions.JOB_TEMPLATES_READ)
        response = await client.get(f"jobbergate/job-script-templates/{parent_id}/upload/workflow")

        assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"
        assert response.content.decode() == "import this"

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_TEMPLATES_DELETE]),
            (False, [Permissions.JOB_TEMPLATES_DELETE, Permissions.ADMIN]),
        ],
    )
    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_template_data,
        synth_bucket,
        synth_services,
        is_owner,
        permissions,
    ):
        parent_id = job_template_data.id
        upserted_instance = await synth_services.file.workflow.upsert(
            parent_id=parent_id,
            filename=WORKFLOW_FILE_NAME,
            upload_content="import this",
            runtime_config=dict(foo="bar"),
        )

        requester_email = tester_email if is_owner else "another_" + tester_email

        inject_security_header(requester_email, *permissions)
        response = await client.delete(f"jobbergate/job-script-templates/{parent_id}/upload/workflow")
        assert response.status_code == status.HTTP_200_OK, f"Delete failed: {response.text}"

        s3_object = await synth_bucket.Object(upserted_instance.file_key)
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()
