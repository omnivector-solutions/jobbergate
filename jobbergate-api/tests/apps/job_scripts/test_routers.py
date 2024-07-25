"""Tests for the /job-scripts/ endpoint."""

import pytest
from fastapi import status

from jobbergate_api.apps.permissions import Permissions

# Not using the synth_session fixture in a route that needs the database is unsafe
pytest.mark.usefixtures("synth_session")


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_CREATE))
async def test_create_stand_alone_job_script__success(
    client, permission, fill_job_script_data, inject_security_header, synth_services
):
    """Test a stand alone job script can be create."""
    payload = fill_job_script_data()

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, permission)

    response = await client.post("jobbergate/job-scripts", json=payload)
    assert response.status_code == 201, f"Create failed: {response.text}"
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["owner_email"] == tester_email
    assert "files" not in response_data
    assert response_data["parent_template_id"] is None

    created_id = response_data["id"]

    # Make sure the data was actually inserted into the database
    assert (await synth_services.crud.job_script.count()) == 1
    instance = await synth_services.crud.job_script.get(created_id)
    assert instance is not None
    assert instance.id == created_id
    assert instance.name == payload["name"]
    assert instance.description == payload["description"]
    assert instance.parent_template_id is None

    # Make sure that the data can be retrieved with a GET request
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
    response = await client.get(f"jobbergate/job-scripts/{created_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["owner_email"] == tester_email
    assert response_data["files"] == []
    assert response_data["parent_template_id"] is None


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_CREATE))
async def test_clone_job_script__success(
    client, permission, fill_job_script_data, inject_security_header, tester_email, synth_services
):
    original_instance = await synth_services.crud.job_script.create(
        **fill_job_script_data(owner_email=tester_email)
    )
    parent_id = original_instance.id
    await synth_services.file.job_script.upsert(
        parent_id=parent_id,
        filename="entrypoint.py",
        upload_content="print('dummy file data')",
        file_type="ENTRYPOINT",
    )
    await synth_services.file.job_script.upsert(
        parent_id=parent_id,
        filename="support.sh",
        upload_content="echo 'dummy file data'",
        file_type="SUPPORT",
    )

    new_owner_email = "new_" + tester_email

    inject_security_header(new_owner_email, permission)
    response = await client.post(f"jobbergate/job-scripts/clone/{original_instance.id}")

    assert response.status_code == 201, f"Clone failed: {response.text}"
    response_data = response.json()

    cloned_id = response_data["id"]

    assert cloned_id != original_instance.id
    assert response_data["name"] == original_instance.name
    assert response_data["description"] == original_instance.description
    assert response_data["owner_email"] == new_owner_email
    assert response_data["cloned_from_id"] == original_instance.id

    assert {f["filename"] for f in response_data["files"]} == {"entrypoint.py", "support.sh"}


async def test_clone_job_script__replace_base_values(
    client, fill_job_script_data, inject_security_header, tester_email, synth_services
):
    original_instance = await synth_services.crud.job_script.create(
        **fill_job_script_data(owner_email=tester_email)
    )

    new_owner_email = "new_" + tester_email

    payload = dict(
        name="new name",
        description="new description",
    )

    inject_security_header(new_owner_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post(f"jobbergate/job-scripts/clone/{original_instance.id}", json=payload)

    assert response.status_code == 201, f"Clone failed: {response.text}"
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["owner_email"] == new_owner_email
    assert response_data["cloned_from_id"] == original_instance.id


async def test_clone_job_script__fail_unauthorized(client, fill_job_script_data, synth_services):
    original_instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    response = await client.post(f"jobbergate/job-scripts/clone/{original_instance.id}")

    assert response.status_code == 401


async def test_clone_job_script__fail_not_found(
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    assert (await synth_services.crud.job_script.count()) == 0
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post("jobbergate/job-scripts/clone/0")

    assert response.status_code == 404


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_CREATE))
async def test_render_job_script_from_template__success(
    permission,
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    dummy_template,
    tester_email,
    job_script_data_as_string,
    synth_services,
):
    """
    Test POST /job_scripts/render-from-template correctly creates a job_script.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint. We show this by asserting that the job_script is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    base_template = await synth_services.crud.template.create(**fill_job_template_data())

    template_name = "entrypoint.sh.j2"
    job_script_name = template_name.removesuffix(".j2")
    await synth_services.file.template.upsert(
        parent_id=base_template.id,
        file_type="ENTRYPOINT",
        filename=template_name,
        upload_content=dummy_template,
    )

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, permission)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED, f"Render failed: {response.text}"

    assert (await synth_services.crud.job_script.count()) == 1

    response_data = response.json()

    assert response_data["name"] == payload["create_request"]["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == payload["create_request"]["description"]
    assert job_script_name in [f["filename"] for f in response_data["files"]]
    assert response_data["parent_template_id"] == base_template.id

    instance = await synth_services.file.job_script.get(response_data["id"], job_script_name)
    rendered_file_contents = await synth_services.file.job_script.get_file_content(instance)
    assert rendered_file_contents.decode("utf-8") == job_script_data_as_string


async def test_render_job_script_from_template__no_entrypoint(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    dummy_template,
    tester_email,
    synth_services,
):
    """
    Test POST /job_scripts/render-from-template raises 400 if no entrypoint is found.
    """
    base_template = await synth_services.crud.template.create(**fill_job_template_data())

    template_name = "entrypoint.sh.j2"
    job_script_name = template_name.removesuffix(".j2")
    await synth_services.file.template.upsert(
        parent_id=base_template.id,
        file_type="SUPPORT",
        filename=template_name,
        upload_content=dummy_template,
    )

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Render failed: {response.text}"
    assert "Exactly one entrypoint file must be specified, got 0" in response.text


async def test_render_job_script_from_template__multiple_entrypoints(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    dummy_template,
    tester_email,
    synth_services,
):
    """
    Test POST /job_scripts/render-from-template raises 400 if more than one entrypoint is found.
    """
    base_template = await synth_services.crud.template.create(**fill_job_template_data())

    template_name_1 = "entrypoint-1.py.j2"
    job_script_name_1 = template_name_1.removesuffix(".j2")
    await synth_services.file.template.upsert(
        parent_id=base_template.id,
        file_type="ENTRYPOINT",
        filename=template_name_1,
        upload_content=dummy_template,
    )
    template_name_2 = "entrypoint-2.py.j2"
    job_script_name_2 = template_name_2.removesuffix(".j2")
    await synth_services.file.template.upsert(
        parent_id=base_template.id,
        file_type="ENTRYPOINT",
        filename=template_name_2,
        upload_content=dummy_template,
    )

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {
                template_name_1: job_script_name_1,
                template_name_2: job_script_name_2,
            },
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Render failed: {response.text}"
    assert "Exactly one entrypoint file must be specified, got 2" in response.text


async def test_render_job_script_from_template__template_file_unavailable(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    base_template = await synth_services.crud.template.create(**fill_job_template_data())

    template_name = "entrypoint.sh.j2"
    job_script_name = template_name.removesuffix(".j2")

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert (await synth_services.crud.job_script.count()) == 0


async def test_render_job_script_from_template__bad_permission(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test that it is not possible to create job_script without proper permission.
    """
    base_template = await synth_services.crud.template.create(**fill_job_template_data())

    template_name = "entrypoint.sh.j2"
    job_script_name = template_name.removesuffix(".j2")
    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, "INVALID_PERMISSION")

    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_render_job_script_from_template__without_template(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    template_name = "entrypoint.sh.j2"
    job_script_name = template_name.removesuffix(".j2")
    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_CREATE)
    response = await client.post(
        "/jobbergate/job-scripts/render-from-template/9999",
        json=payload,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_READ))
async def test_get_job_script_by_id__success(
    permission,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    inserted_instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    inject_security_header(tester_email, permission)
    response = await client.get(f"/jobbergate/job-scripts/{inserted_instance.id}")

    assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"

    data = response.json()
    assert data["id"] == inserted_instance.id
    assert data["name"] == inserted_instance.name
    assert data["owner_email"] == inserted_instance.owner_email
    assert data["parent_template_id"] is None
    assert data["files"] == []


async def test_get_job_script_by_id__invalid_id(
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test the correct response code is returned when a job_script does not exist.

    This test proves that GET /job-script/<id> returns the correct response code when the
    requested job_script does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_script requested doesn't exist (404).
    """
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
    response = await client.get("/jobbergate/job-scripts/9999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_job_script_by_id__bad_permission(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    inserted_instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-scripts/{inserted_instance.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_SCRIPTS_UPDATE]),
        (False, [Permissions.ADMIN]),
        (False, [Permissions.JOB_SCRIPTS_UPDATE, Permissions.MAINTAINER]),
    ],
)
async def test_update_job_script__success(
    client,
    fill_job_script_data,
    inject_security_header,
    tester_email,
    synth_services,
    is_owner,
    permissions,
):
    instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    requester_email = tester_email if is_owner else "another_" + tester_email

    payload = dict(
        name="new-name",
        description="new-description",
    )

    inject_security_header(requester_email, *permissions)
    response = await client.put(f"jobbergate/job-scripts/{instance.id}", json=payload)

    assert response.status_code == 200, f"Update failed: {response.text}"
    response_data = response.json()
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]


async def test_update_job_script__fail_not_found(
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    payload = dict(
        name="new-name",
        description="new-description",
    )
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_UPDATE)
    response = await client.put("jobbergate/job-scripts/0", json=payload)

    assert response.status_code == 404


async def test_update_job_script__fail_unauthorized(client):
    payload = dict(
        name="new-name",
        description="new-description",
    )
    response = await client.put("jobbergate/job-scripts/0", json=payload)

    assert response.status_code == 401


async def test_update_job_script__fail_forbidden(
    client,
    fill_job_script_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    owner_email = tester_email
    requester_email = "another_" + owner_email

    payload = dict(
        name="new-name",
        description="new-description",
    )

    inject_security_header(requester_email, Permissions.JOB_SCRIPTS_UPDATE)
    response = await client.put(f"jobbergate/job-scripts/{instance.id}", json=payload)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_SCRIPTS_DELETE]),
        (False, [Permissions.ADMIN]),
        (False, [Permissions.JOB_SCRIPTS_DELETE, Permissions.MAINTAINER]),
    ],
)
async def test_delete_job_script__success(
    client,
    inject_security_header,
    fill_job_script_data,
    synth_services,
    is_owner,
    permissions,
):
    instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    owner_email = instance.owner_email
    requester_email = owner_email if is_owner else "another_" + owner_email

    inject_security_header(requester_email, *permissions)
    response = await client.delete(f"jobbergate/job-scripts/{instance.id}")
    assert response.status_code == 204, f"Delete failed: {response.text}"

    assert (await synth_services.crud.job_script.count()) == 0


async def test_delete_job_script__fail_not_found(
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_DELETE)
    response = await client.delete("jobbergate/job-scripts/0")
    assert response.status_code == 404


async def test_delete_job_script__fail_forbidden(
    client,
    inject_security_header,
    fill_job_script_data,
    synth_services,
):
    instance = await synth_services.crud.job_script.create(**fill_job_script_data())

    owner_email = instance.owner_email
    requester_email = "another_" + owner_email

    inject_security_header(requester_email, Permissions.JOB_SCRIPTS_DELETE)
    response = await client.delete(f"jobbergate/job-scripts/{instance.id}")
    assert response.status_code == 403

    assert (await synth_services.crud.job_script.count()) == 1


class TestListJobScripts:
    """Test the list endpoint."""

    @pytest.fixture(scope="function")
    async def job_scripts_list(self, fill_all_job_script_data, synth_services):
        data = fill_all_job_script_data(
            {
                "name": "name-1",
                "description": "desc-1",
            },
            {
                "name": "name-2",
                "description": "desc-2",
            },
            {
                "name": "name-3",
                "description": "desc-3",
            },
            {
                "name": "name-4",
                "description": "desc-4",
                "owner_email": "test-test@pytest.com",
            },
            {
                "name": "name-5",
                "description": "desc-5",
                "owner_email": "test-test@pytest.com",
                "is_archived": True,
            },
        )
        for item in data:
            await synth_services.crud.job_script.create(**item)
        yield data

    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_READ))
    async def test_list_job_scripts__all_success(
        self,
        permission,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, permission)
        response = await client.get("jobbergate/job-scripts?include_archived=True&sort_field=id")
        assert response.status_code == 200, f"Get failed: {response.text}"

        response_data = response.json()
        assert response_data["total"] == len(job_scripts_list)
        assert response_data["page"] == 1
        assert response_data["size"] == 50
        assert response_data["pages"] == 1

        for response_item, expected_item in zip(response_data["items"], job_scripts_list):
            assert response_item["name"] == expected_item["name"]
            assert response_item["description"] == expected_item["description"]
            assert response_item["owner_email"] == expected_item["owner_email"]
            assert response_item["is_archived"] == expected_item["is_archived"]
            assert response_item["template"] is None

    async def test_list_job_scripts__ignore_archived(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
        response = await client.get("jobbergate/job-scripts")
        assert response.status_code == 200, f"Get failed: {response.text}"

        response_data = response.json()

        expected_names = {i["name"] for i in job_scripts_list if i["is_archived"] is False}
        response_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == response_names

    async def test_list_job_scripts__user_only(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
        response = await client.get("jobbergate/job-scripts?user_only=True&include_archived=True")
        assert response.status_code == 200, f"Get failed: {response.text}"

        response_data = response.json()

        expected_names = {i["name"] for i in job_scripts_list if i["owner_email"] == tester_email}
        actual_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == actual_names

    async def test_list_job_scripts__with_parent(
        self,
        client,
        tester_email,
        inject_security_header,
        fill_job_template_data,
        fill_all_job_script_data,
        synth_services,
        job_script_data_as_string,
    ):
        base_template = await synth_services.crud.template.create(**fill_job_template_data())

        data = fill_all_job_script_data(
            {"name": "name-1", "parent_template_id": base_template.id},
            {"name": "name-2"},
        )

        for item in data:
            job_script_data = await synth_services.crud.job_script.create(**item)

            id = job_script_data.id
            file_type = "ENTRYPOINT"
            job_script_filename = "entrypoint.sh"

            await synth_services.file.job_script.upsert(
                parent_id=id,
                filename=job_script_filename,
                upload_content=job_script_data_as_string,
                file_type=file_type,
            )

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
        response = await client.get("jobbergate/job-scripts")
        assert response.status_code == 200, f"Get failed: {response.text}"

        response_data = response.json()

        expected_names = {i["name"] for i in data}
        actual_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == actual_names

        assert response_data["items"][0]["template"] is not None
        assert response_data["items"][0]["template"]["name"] == base_template.name
        assert response_data["items"][1]["template"] is None

    async def test_list_job_scripts__search(
        self,
        client,
        tester_email,
        inject_security_header,
        fill_all_job_script_data,
        synth_services,
    ):
        data = fill_all_job_script_data(
            dict(
                name="instance-one",
                description="the first",
                owner_email="user1@test.com",
            ),
            dict(
                name="item-two",
                description="second item",
                owner_email="user2@test.com",
            ),
            dict(
                name="instance-three",
                description="a final instance",
                owner_email="final@test.com",
            ),
        )

        for item in data:
            await synth_services.crud.job_script.create(**item)

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
        response = await client.get("jobbergate/job-scripts", params={"search": "instance"})
        assert response.status_code == 200, f"Get failed: {response.text}"

        response_data = response.json()

        expected_names = {"instance-one", "instance-three"}
        actual_names = {i["name"] for i in response_data["items"]}

        assert response_data["total"] == len(expected_names)
        assert expected_names == actual_names


class TestJobScriptFiles:
    @pytest.fixture(scope="function")
    async def job_script_data(self, fill_job_script_data, synth_services):
        raw_db_data = await synth_services.crud.job_script.create(**fill_job_script_data())
        yield raw_db_data

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_SCRIPTS_CREATE]),
            (False, [Permissions.ADMIN]),
            (False, [Permissions.JOB_SCRIPTS_CREATE, Permissions.MAINTAINER]),
        ],
    )
    async def test_upsert_new_file(
        self,
        client,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        make_dummy_file,
        synth_services,
        is_owner,
        permissions,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.sh", content=job_script_data_as_string)

        owner_email = job_script_data.owner_email
        requester_email = owner_email if is_owner else "another_" + owner_email

        inject_security_header(requester_email, *permissions)
        with open(dummy_file_path, mode="rb") as file:
            response = await client.put(
                f"jobbergate/job-scripts/{id}/upload/{file_type}",
                files={"upload_file": (dummy_file_path.name, file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        # Check the response from the upload endpoint
        response_data = response.json()
        assert response_data is not None
        assert response_data["parent_id"] == id
        assert response_data["filename"] == dummy_file_path.name
        assert response_data["file_type"] == file_type

        # Check the database
        job_script_file = await synth_services.file.job_script.get(id, "test_template.sh")
        assert job_script_file is not None
        assert job_script_file.parent_id == id
        assert job_script_file.filename == dummy_file_path.name
        assert job_script_file.file_type == file_type
        assert job_script_file.file_key == f"job_script_files/{id}/{dummy_file_path.name}"

        # Check the file content on s3
        file_content = await synth_services.file.job_script.get_file_content(job_script_file)
        assert file_content.decode() == job_script_data_as_string

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_SCRIPTS_CREATE]),
            (False, [Permissions.ADMIN]),
            (False, [Permissions.JOB_SCRIPTS_CREATE, Permissions.MAINTAINER]),
        ],
    )
    async def test_upsert_replace_content(
        self,
        client,
        inject_security_header,
        job_script_data,
        make_dummy_file,
        synth_services,
        is_owner,
        permissions,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=id,
            filename=job_script_filename,
            upload_content="original_content",
            file_type=file_type,
        )

        new_content = "new_content"
        dummy_file_path = make_dummy_file(job_script_filename, content=new_content)

        owner_email = job_script_data.owner_email
        requester_email = owner_email if is_owner else "another_" + owner_email
        inject_security_header(requester_email, *permissions)
        with open(dummy_file_path, mode="rb") as file:
            response = await client.put(
                f"jobbergate/job-scripts/{id}/upload/{file_type}",
                files={"upload_file": (dummy_file_path.name, file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        job_script_file = await synth_services.file.job_script.get(id, job_script_filename)

        assert job_script_file is not None
        assert job_script_file.parent_id == id
        assert job_script_file.filename == job_script_filename
        assert job_script_file.file_type == file_type
        assert job_script_file.file_key == f"job_script_files/{id}/{dummy_file_path.name}"

        file_content = await synth_services.file.job_script.get_file_content(job_script_file)
        assert file_content.decode() == new_content

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_SCRIPTS_CREATE]),
            (False, [Permissions.ADMIN]),
            (False, [Permissions.JOB_SCRIPTS_CREATE, Permissions.MAINTAINER]),
        ],
    )
    async def test_upsert_rename_file(
        self,
        client,
        inject_security_header,
        job_script_data,
        synth_services,
        is_owner,
        permissions,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=id,
            filename=job_script_filename,
            upload_content="original_content",
            file_type=file_type,
        )

        new_filename = "new_filename.sh"

        owner_email = job_script_data.owner_email
        requester_email = owner_email if is_owner else "another_" + owner_email
        inject_security_header(requester_email, *permissions)
        response = await client.put(
            f"jobbergate/job-scripts/{id}/upload/{file_type}",
            params={"filename": new_filename, "previous_filename": job_script_filename},
        )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        job_script_file = await synth_services.file.job_script.get(id, new_filename)

        assert job_script_file is not None
        assert job_script_file.parent_id == id
        assert job_script_file.filename == new_filename
        assert job_script_file.file_type == file_type
        assert job_script_file.file_key == f"job_script_files/{id}/{new_filename}"

        file_content = await synth_services.file.job_script.get_file_content(job_script_file)
        assert file_content.decode() == "original_content"

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_SCRIPTS_CREATE]),
            (False, [Permissions.ADMIN]),
            (False, [Permissions.JOB_SCRIPTS_CREATE, Permissions.MAINTAINER]),
        ],
    )
    async def test_upsert_replace_content_and_rename(
        self,
        client,
        inject_security_header,
        job_script_data,
        make_dummy_file,
        synth_services,
        is_owner,
        permissions,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=id,
            filename=job_script_filename,
            upload_content="original_content",
            file_type=file_type,
        )

        new_content = "new_content"
        new_filename = "new_filename.sh"

        dummy_file_path = make_dummy_file(new_filename, content=new_content)
        owner_email = job_script_data.owner_email
        requester_email = owner_email if is_owner else "another_" + owner_email
        inject_security_header(requester_email, *permissions)
        with open(dummy_file_path, mode="rb") as file:
            response = await client.put(
                f"jobbergate/job-scripts/{id}/upload/{file_type}",
                files={"upload_file": (dummy_file_path.name, file, "text/plain")},
                params={
                    "filename": dummy_file_path.name,
                    "previous_filename": job_script_filename,
                },
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        job_script_file = await synth_services.file.job_script.get(id, new_filename)

        assert job_script_file is not None
        assert job_script_file.parent_id == id
        assert job_script_file.filename == new_filename
        assert job_script_file.file_type == file_type
        assert job_script_file.file_key == f"job_script_files/{id}/{new_filename}"

        file_content = await synth_services.file.job_script.get_file_content(job_script_file)
        assert file_content.decode() == new_content

    async def test_create__fail_forbidden(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        make_dummy_file,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.sh", content=job_script_data_as_string)

        owner_email = tester_email
        requester_email = "another_" + owner_email

        inject_security_header(requester_email, Permissions.JOB_SCRIPTS_CREATE)
        with open(dummy_file_path, mode="rb") as file:
            response = await client.put(
                f"jobbergate/job-scripts/{id}/upload/{file_type}",
                files={"upload_file": (dummy_file_path.name, file, "text/plain")},
                params={"filename": dummy_file_path.name},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_READ))
    async def test_get__success(
        self,
        permission,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        synth_services,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=id,
            filename=job_script_filename,
            upload_content=job_script_data_as_string,
            file_type=file_type,
        )

        inject_security_header(tester_email, permission)
        response = await client.get(f"jobbergate/job-scripts/{id}/upload/{job_script_filename}")

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == job_script_data_as_string

    async def test_get__large_file_success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        synth_services,
    ):
        """
        Ensure that large files can be retrieved with no problem.
        This was created after strange issues were identified running on FastAPI 0.111.
        """
        large_string = "print(1)\n" * 5000

        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=id,
            filename=job_script_filename,
            upload_content=large_string,
            file_type=file_type,
        )

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_READ)
        response = await client.get(f"jobbergate/job-scripts/{id}/upload/{job_script_filename}")

        assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"
        assert response.content.decode() == large_string

    @pytest.mark.parametrize(
        "is_owner, permissions",
        [
            (True, [Permissions.JOB_SCRIPTS_DELETE]),
            (False, [Permissions.ADMIN]),
            (False, [Permissions.JOB_SCRIPTS_DELETE, Permissions.MAINTAINER]),
        ],
    )
    async def test_delete__success(
        self,
        client,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        synth_services,
        synth_bucket,
        is_owner,
        permissions,
    ):
        parent_id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        upserted_instance = await synth_services.file.job_script.upsert(
            parent_id=parent_id,
            filename=job_script_filename,
            upload_content=job_script_data_as_string,
            file_type=file_type,
        )

        owner_email = job_script_data.owner_email
        requester_email = owner_email if is_owner else "another_" + owner_email

        inject_security_header(requester_email, *permissions)
        response = await client.delete(f"jobbergate/job-scripts/{parent_id}/upload/{job_script_filename}")
        assert response.status_code == status.HTTP_200_OK, f"Delete failed: {response.text}"

        s3_object = await synth_bucket.Object(upserted_instance.file_key)
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()

    async def test_delete__fail_forbidden(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        synth_services,
    ):
        parent_id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.sh"

        await synth_services.file.job_script.upsert(
            parent_id=parent_id,
            filename=job_script_filename,
            upload_content=job_script_data_as_string,
            file_type=file_type,
        )

        owner_email = tester_email
        requester_email = "another_" + owner_email

        inject_security_header(requester_email, Permissions.JOB_SCRIPTS_DELETE)
        response = await client.delete(f"jobbergate/job-scripts/{parent_id}/upload/{job_script_filename}")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SCRIPTS_DELETE))
async def test_auto_clean_unused_entries(
    client, permission, tester_email, inject_security_header, synth_session
):
    """Test that unused job scripts are automatically cleaned."""
    inject_security_header(tester_email, permission)
    response = await client.delete("jobbergate/job-scripts/clean-unused-entries")
    assert response.status_code == status.HTTP_202_ACCEPTED
