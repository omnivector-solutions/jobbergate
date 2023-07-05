"""Tests for the /job-scripts/ endpoint."""
import json
from textwrap import dedent

import pytest
from fastapi import status

from jobbergate_api.apps.job_scripts.schemas import JobScriptResponse
from jobbergate_api.apps.permissions import Permissions


@pytest.fixture
def job_script_data_as_string():
    """
    Provide a fixture that returns an example of a default application script.
    """
    content = dedent(
        """
                #!/bin/bash

                #SBATCH --job-name=rats
                #SBATCH --partition=debug
                #SBATCH --time=00:30:00
                #SBATCH --partition=debug
                #SBATCH --output=sample-%j.out


                echo $SLURM_TASKS_PER_NODE
                echo $SLURM_SUBMIT_DIR
                """
    ).strip()
    return content


@pytest.mark.asyncio
async def test_create_stand_alone_job_script(
    job_script_service, client, fill_job_script_data, inject_security_header, time_frame
):
    """Test a stand alone job script can be create."""
    assert (await job_script_service.count()) == 0

    payload = fill_job_script_data()

    tester_email = payload.pop("owner_email")
    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)

    with time_frame() as window:
        response = await client.post("jobbergate/job-scripts", json=payload)

    assert response.status_code == 201

    response_data = JobScriptResponse(**response.json())

    assert response_data.name == payload["name"]
    assert response_data.description == payload["description"]
    assert response_data.owner_email == tester_email
    assert response_data.updated_at in window
    assert response_data.created_at in window
    assert response_data.files == {}
    assert response_data.parent_template_id is None

    raw_db_data = await job_script_service.get(response_data.id)
    db_data = JobScriptResponse.from_orm(raw_db_data)

    assert db_data == response_data

    assert (await job_script_service.count()) == 1


@pytest.mark.asyncio
async def test_render_job_script_from_template(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    time_frame,
    dummy_template,
    tester_email,
    job_script_data_as_string,
    template_service,
    template_file_service,
    job_script_service,
    job_script_files_service,
):
    """
    Test POST /job_scripts/render-from-template correctly creates a job_script.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint. We show this by asserting that the job_script is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    base_template = await template_service.create(**fill_job_template_data())
    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")
    template_file = await template_file_service.upsert(
        id=base_template.id,
        file_type="ENTRYPOINT",
        filename=template_name,
        upload_content=dummy_template,
    )
    await template_service.db_session.commit()

    assert (await job_script_service.count()) == 0

    payload = {
        "create_request": fill_job_script_data(),
        "render_request": {
            "template_output_name_mapping": {template_name: job_script_name},
            "sbatch_params": ["--partition=debug", "--time=00:30:00"],
            "param_dict": {"data": {"job_name": "rats", "partition": "debug"}},
        },
    }

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
    with time_frame() as window:
        response = await client.post(
            f"/jobbergate/job-scripts/render-from-template/{base_template.id}",
            json=payload,
        )

    assert response.status_code == status.HTTP_201_CREATED

    assert (await job_script_service.count()) == 1

    response_data = JobScriptResponse.parse_obj(response.json())

    raw_db_data = await job_script_service.get(response_data.id)
    db_data = JobScriptResponse.from_orm(raw_db_data)

    assert db_data == response_data

    assert response_data.name == payload["create_request"]["name"]
    assert response_data.owner_email == tester_email
    assert response_data.description == payload["create_request"]["description"]
    assert job_script_name in response_data.files
    assert response_data.parent_template_id == base_template.id
    assert response_data.created_at in window
    assert response_data.updated_at in window

    actual_job_script_file = await job_script_files_service.get(raw_db_data.files[job_script_name])

    assert actual_job_script_file.decode("utf-8") == job_script_data_as_string


@pytest.mark.asyncio
async def test_render_job_script_from_template__template_file_unavailable(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    template_service,
    job_script_service,
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    base_template = await template_service.create(**fill_job_template_data())
    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")
    await template_service.db_session.commit()

    assert (await job_script_service.count()) == 0

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

    assert (await job_script_service.count()) == 0


@pytest.mark.asyncio
async def test_render_job_script_from_template__bad_permission(
    fill_job_template_data,
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    template_service,
    job_script_service,
):
    """
    Test that it is not possible to create job_script without proper permission.
    """
    base_template = await template_service.create(**fill_job_template_data())
    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")
    await template_service.db_session.commit()

    assert (await job_script_service.count()) == 0

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

    assert (await job_script_service.count()) == 0


@pytest.mark.asyncio
async def test_render_job_script_from_template__without_template(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    job_script_service,
):
    """
    Test POST /job_scripts/render-from-template can't create a job_script if the template file is unavailable.
    """
    template_name = "entrypoint.py.j2"
    job_script_name = template_name.removesuffix(".j2")

    assert (await job_script_service.count()) == 0

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

    assert (await job_script_service.count()) == 0


@pytest.mark.asyncio
async def test_get_job_script_by_id__success(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    job_script_filename = "entrypoint.py"
    raw_db_data = await job_script_service.create(**fill_job_script_data())
    raw_job_script_file = await job_script_files_service.upsert(
        id=raw_db_data.id,
        file_type="ENTRYPOINT",
        filename=job_script_filename,
        upload_content=job_script_data_as_string,
    )

    await job_script_service.db_session.commit()

    inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"/jobbergate/job-scripts/{raw_db_data.id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == raw_db_data.id
    assert data["name"] == raw_db_data.name
    assert data["owner_email"] == raw_db_data.owner_email
    assert data["parent_template_id"] is None

    job_script_file = data["files"].get(job_script_filename)

    assert job_script_file is not None
    assert job_script_file["id"] == raw_job_script_file.id
    assert job_script_file["filename"] == job_script_filename
    assert job_script_file["file_type"] == "ENTRYPOINT"
    assert job_script_file["path"] == f"/jobbergate/job-scripts/{raw_db_data.id}/upload/{job_script_filename}"


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_get_job_script_by_id__bad_permission(
    fill_job_script_data,
    client,
    inject_security_header,
    tester_email,
    job_script_service,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    raw_db_data = await job_script_service.create(**fill_job_script_data())
    await job_script_service.db_session.commit()

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-scripts/{raw_db_data.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListJobScripts:
    """Test the list endpoint."""

    @pytest.mark.asyncio
    @pytest.fixture(scope="function")
    async def job_scripts_list(self, job_script_service, fill_all_job_script_data):
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
        for item in data:
            await job_script_service.create(**item)
        await job_script_service.db_session.commit()
        yield data

    @pytest.mark.asyncio
    async def test_list_job_scripts__all_success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get("jobbergate/job-scripts")
        assert response.status_code == 200

        actual_data = response.json()
        assert actual_data["total"] == len(job_scripts_list)
        assert actual_data["page"] == 1
        assert actual_data["size"] == 50
        assert actual_data["pages"] == 1

        for actual_item, expected_item in zip(actual_data["items"], job_scripts_list):
            assert actual_item["name"] == expected_item["name"]
            assert actual_item["description"] == expected_item["description"]
            assert actual_item["owner_email"] == expected_item["owner_email"]
            assert actual_item["files"] == {}

    @pytest.mark.asyncio
    async def test_list_job_scripts__user_only(
        self,
        client,
        tester_email,
        inject_security_header,
        job_scripts_list,
    ):
        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get("jobbergate/job-scripts?user_only=True")
        assert response.status_code == 200

        actual_data = response.json()
        assert actual_data["total"] == 3

        expected_names = {i["name"] for i in job_scripts_list if i["owner_email"] == tester_email}
        actual_names = {i["name"] for i in actual_data["items"]}

        assert expected_names == actual_names


class TestJobScriptFiles:
    @pytest.fixture(scope="function")
    async def job_script_data(self, fill_job_script_data, job_script_service):
        raw_db_data = await job_script_service.create(**fill_job_script_data())
        await job_script_service.db_session.commit()
        await job_script_service.db_session.refresh(raw_db_data)
        yield raw_db_data

    @pytest.mark.asyncio
    async def test_create__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        make_dummy_file,
        job_script_service,
        job_script_files_service,
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

        assert response.status_code == status.HTTP_200_OK

        await job_script_service.db_session.refresh(job_script_data)

        job_script_file = job_script_data.files.get(dummy_file_path.name)

        assert job_script_file is not None

        assert job_script_file.id == id
        assert job_script_file.filename == dummy_file_path.name
        assert job_script_file.file_type == file_type
        assert job_script_file.file_key == f"job_script_files/{id}/{dummy_file_path.name}"

        file_content = await job_script_files_service.get(job_script_file)
        assert file_content.decode() == job_script_data_as_string

    @pytest.mark.asyncio
    async def test_get__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        job_script_files_service,
        synth_bucket,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.py"

        await job_script_files_service.upsert(
            id=id,
            file_type=file_type,
            filename=job_script_filename,
            upload_content=job_script_data_as_string,
        )
        await job_script_files_service.db_session.commit()

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_VIEW)
        response = await client.get(f"jobbergate/job-scripts/{id}/upload/{job_script_filename}")

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == job_script_data_as_string

    @pytest.mark.asyncio
    async def test_delete__success(
        self,
        client,
        tester_email,
        inject_security_header,
        job_script_data,
        job_script_data_as_string,
        job_script_files_service,
        synth_bucket,
    ):
        id = job_script_data.id
        file_type = "ENTRYPOINT"
        job_script_filename = "entrypoint.py"

        job_script_file_db = await job_script_files_service.upsert(
            id=id,
            file_type=file_type,
            filename=job_script_filename,
            upload_content=job_script_data_as_string,
        )
        await job_script_files_service.db_session.commit()

        inject_security_header(tester_email, Permissions.JOB_SCRIPTS_EDIT)
        response = await client.delete(f"jobbergate/job-scripts/{id}/upload/{job_script_filename}")
        assert response.status_code == status.HTTP_200_OK

        s3_object = await synth_bucket.Object(job_script_file_db.file_key)
        with pytest.raises(synth_bucket.meta.client.exceptions.NoSuchKey):
            await s3_object.get()
