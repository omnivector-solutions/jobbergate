"""Tests for the /job-scripts/ endpoint."""
import pytest
from fastapi import HTTPException, status

from jobbergate_api.apps.job_script_templates.services import crud_service as template_crud_service
from jobbergate_api.apps.job_script_templates.services import template_file_service
from jobbergate_api.apps.job_scripts.schemas import JobScriptResponse
from jobbergate_api.apps.job_scripts.services import crud_service, file_service
from jobbergate_api.apps.permissions import Permissions

# Not using the synth_session fixture in a route that needs the database is unsafe
pytest.mark.usefixtures("synth_session")


async def test_create_stand_alone_job_script(
    client, fill_job_script_data, inject_security_header, synth_session
):
    """Test a stand alone job script can be create."""
    payload = fill_job_script_data()

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)

    response = await client.post("jobbergate/job-scripts", json=payload)
    assert response.status_code == 201, f"Create failed: {response.text}"
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["owner_email"] == tester_email
    assert response_data["files"] == []
    assert response_data["parent_template_id"] is None

    created_id = response_data["id"]

    # Make sure that the crud service has no bound session after the request is complete
    with pytest.raises(HTTPException) as exc_info:
        crud_service.session
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service is not bound to a database session"

    # Make sure the data was actually inserted into the database
    with crud_service.bound_session(synth_session):
        assert (await crud_service.count()) == 1
        instance = await crud_service.get(created_id)
        assert instance is not None
        assert instance.id == created_id
        assert instance.name == payload["name"]
        assert instance.description == payload["description"]
        assert instance.parent_template_id is None

    # Make sure that the data can be retrieved with a GET request
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"jobbergate/job-scripts/{created_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["owner_email"] == tester_email
    assert response_data["files"] == []
    assert response_data["parent_template_id"] is None


async def test_render_job_script_from_template(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    dummy_template,
    tester_email,
    job_script_data_as_string,
    synth_session,
    synth_bucket,
):
    """
    Test POST /job_scripts/render-from-template correctly creates a job_script.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint. We show this by asserting that the job_script is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    with template_crud_service.bound_session(synth_session):
        base_template = await template_crud_service.create(**fill_job_template_data())

    with template_file_service.bound_session(synth_session):
        with template_file_service.bound_bucket(synth_bucket):

            template_name = "entrypoint.py.j2"
            job_script_name = template_name.removesuffix(".j2")
            await template_file_service.upsert(
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

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_201_CREATED, f"Render failed: {response.text}"

    with crud_service.bound_session(synth_session):
        assert (await crud_service.count()) == 1

    response_data = response.json()

    assert response_data["name"] == payload["create_request"]["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == payload["create_request"]["description"]
    assert job_script_name in [f["filename"] for f in response_data["files"]]
    assert response_data["parent_template_id"] == base_template.id

    with file_service.bound_session(synth_session):
        with file_service.bound_bucket(synth_bucket):
            instance = await file_service.get(response_data["id"], job_script_name)
            rendered_file_contents = await file_service.get_file_content(instance)
            assert rendered_file_contents.decode("utf-8") == job_script_data_as_string


async def test_render_job_script_from_template__template_file_unavailable(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    with template_crud_service.bound_session(synth_session):
        base_template = await template_crud_service.create(**fill_job_template_data())

    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
    response = await client.post(
        f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    with crud_service.bound_session(synth_session):
        assert (await crud_service.count()) == 0


async def test_render_job_script_from_template__bad_permission(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test that it is not possible to create job_script without proper permission.
    """
    with template_crud_service.bound_session(synth_session):
        base_template = await template_crud_service.create(**fill_job_template_data())

    template_name = "entrypoint.py.j2"
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
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")
    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
    response = await client.post(
        "/jobbergate/job-scripts/render-from-template/9999",
        json=payload,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_job_script_by_id__success(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    with crud_service.bound_session(synth_session):
        inserted_instance = await crud_service.create(**fill_job_script_data())

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
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
):
    """
    Test the correct response code is returned when a job_script does not exist.

    This test proves that GET /job-script/<id> returns the correct response code when the
    requested job_script does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_script requested doesn't exist (404).
    """
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/9999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_job_script_by_id__bad_permission(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    synth_session,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    with crud_service.bound_session(synth_session):
        inserted_instance = await crud_service.create(**fill_job_script_data())

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-scripts/{inserted_instance.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListJobScripts:
    """Test the list endpoint."""

    @pytest.fixture(scope="function")
    async def job_scripts_list(self, fill_all_job_script_data, synth_session):
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
        )
        with crud_service.bound_session(synth_session):
            for item in data:
                await crud_service.create(**item)
        yield data

    async def test_list_job_scripts__all_success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get("jobbergate/job-scripts")
        assert response.status_code == 200, f"Get failed: {response.text}"

        actual_data = response.json()
        assert actual_data["total"] == len(job_scripts_list)
        assert actual_data["page"] == 1
        assert actual_data["size"] == 50
        assert actual_data["pages"] == 1

        for actual_item, expected_item in zip(actual_data["items"], job_scripts_list):
            assert actual_item["name"] == expected_item["name"]
            assert actual_item["description"] == expected_item["description"]
            assert actual_item["owner_email"] == expected_item["owner_email"]
            assert actual_item["files"] == []

    async def test_list_job_scripts__user_only(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get("jobbergate/job-scripts?user_only=True")
        assert response.status_code == 200, f"Get failed: {response.text}"

        actual_data = response.json()
        assert actual_data["total"] == 3

        expected_names = {i["name"] for i in job_scripts_list if i["owner_email"] == tester_email}
        actual_names = {i["name"] for i in actual_data["items"]}
        assert expected_names == actual_names


class TestJobScriptFiles:
    @pytest.fixture(scope="function")
    async def job_script_data(self, fill_job_script_data, synth_session):
        with crud_service.bound_session(synth_session):
            raw_db_data = await crud_service.create(**fill_job_script_data())
        yield raw_db_data

    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        make_dummy_file,
        synth_session,
        synth_bucket,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        dummy_file_path = make_dummy_file("test_template.py", content=job_script_data_as_string)

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
        with open(dummy_file_path, mode="rb") as file:
            response = await client.put(
                f"jobbergate/job-scripts/{id}/upload/{file_type}",
                files={"upload_file": (dummy_file_path.name, file, "text/plain")},
            )

        assert response.status_code == status.HTTP_200_OK, f"Upsert failed: {response.text}"

        with file_service.bound_session(synth_session):
            with file_service.bound_bucket(synth_bucket):
                job_script_file = await file_service.get(id, "test_template.py")

                assert job_script_file is not None
                assert job_script_file.parent_id == id
                assert job_script_file.filename == dummy_file_path.name
                assert job_script_file.file_type == file_type
                assert job_script_file.file_key == f"job_script_files/{id}/{dummy_file_path.name}"

                file_content = await file_service.get_file_content(job_script_file)
                assert file_content.decode() == job_script_data_as_string

    async def test_get__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        synth_session,
        synth_bucket,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.py"

        with file_service.bound_session(synth_session):
            with file_service.bound_bucket(synth_bucket):
                await file_service.upsert(
                    parent_id=id,
                    filename=job_script_filename,
                    upload_content=job_script_data_as_string,
                    file_type=file_type,
                )

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get(f"jobbergate/job-scripts/{id}/upload/{job_script_filename}")

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == job_script_data_as_string

    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        synth_session,
        synth_bucket,
    ):
        parent_id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.py"

        with file_service.bound_session(synth_session):
            with file_service.bound_bucket(synth_bucket):
                upserted_instance = await file_service.upsert(
                    parent_id=parent_id,
                    filename=job_script_filename,
                    upload_content=job_script_data_as_string,
                    file_type=file_type,
                )

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
        response = await client.delete(f"jobbergate/job-scripts/{parent_id}/upload/{job_script_filename}")
        assert response.status_code == status.HTTP_200_OK, f"Delete failed: {response.text}"

        s3_object = await synth_bucket.Object(upserted_instance.file_key)
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()
