"""
Tests for the /job-scripts/ endpoint.
"""
import pathlib
from textwrap import dedent
from unittest import mock

import pytest
from fastapi import status

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_scripts.schemas import JobScriptResponse
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import fetch_all, fetch_count, fetch_instance, insert_data


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
                #SBATCH --output=sample-%j.out


                echo $SLURM_TASKS_PER_NODE
                echo $SLURM_SUBMIT_DIR
                """
    ).strip()
    return content


@pytest.fixture
def new_job_script_data_as_string():
    """
    Provide a fixture that returns an application script after the injection of the sbatch params.
    """
    content = dedent(
        """
                #!/bin/bash

                #SBATCH --comment=some_comment
                #SBATCH --nice=-1
                #SBATCH -N 10
                #SBATCH --job-name=rats
                #SBATCH --partition=debug
                #SBATCH --output=sample-%j.out


                echo $SLURM_TASKS_PER_NODE
                echo $SLURM_SUBMIT_DIR
                """
    ).strip()
    return content


@pytest.fixture
def sbatch_params():
    """
    Provide a fixture that returns string content of the argument --sbatch-params.
    """
    return ["--comment=some_comment", "--nice=-1", "-N 10"]


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.job_scripts.job_script_files.JobScriptFiles.write_to_s3")
async def test_create_job_script__with_application(
    mocked_write_job_script_files_to_s3,
    synth_session,
    fill_application_data,
    job_script_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
    time_frame,
    dummy_application_config,
    dummy_application_source_file,
    dummy_template,
    job_script_data_as_string,
    mocked_file_manager_factory,
):
    """
    Test POST /job_scripts/ correctly creates a job_script with a source application.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint. We show this by asserting that the job_script is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
            application_uploaded=True,
        ),
    )

    ApplicationFiles(
        templates={"test_job_script.sh": dummy_template},
        source_file=dummy_application_source_file,
        config_file=dummy_application_config,
    ).write_to_s3(inserted_application_id)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with time_frame() as window:
        response = await client.post(
            "/jobbergate/job-scripts/",
            json=fill_job_script_data(
                application_id=inserted_application_id,
                param_dict=param_dict,
            ),
        )

    assert response.status_code == status.HTTP_201_CREATED
    rows = await fetch_all(synth_session, job_scripts_table, JobScriptResponse)
    assert len(rows) == 1

    job_script = JobScriptResponse(**response.json())

    mocked_write_job_script_files_to_s3.assert_called_once_with(job_script.id, override_bucket_name=None)

    assert job_script.id == rows[0].id
    assert job_script.job_script_name == job_script_data["job_script_name"]
    assert job_script.job_script_owner_email == "owner1@org.com"
    assert job_script.job_script_description == ""
    assert job_script.job_script_files.main_file
    assert job_script.application_id == inserted_application_id
    assert job_script.created_at in window
    assert job_script.updated_at in window
    assert job_script.job_script_files.main_file == job_script_data_as_string


@pytest.mark.asyncio
async def test_create_job_script__without_application(
    synth_session,
    job_script_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
    time_frame,
):
    """
    Test POST /job_scripts/ correctly creates a job_script without a source application.

    This test proves that a job_script is successfully created via a POST request to the /job-scripts/
    endpoint without specifying a source application_id. We show this by asserting that the job_script is
    created in the database after the post request is made, the correct status code (201) is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with time_frame() as window:
        response = await client.post(
            "/jobbergate/job-scripts/",
            json=fill_job_script_data(
                param_dict=param_dict,
            ),
        )

    assert response.status_code == status.HTTP_201_CREATED

    rows = await fetch_all(synth_session, job_scripts_table, JobScriptResponse)
    assert len(rows) == 1

    job_script = JobScriptResponse(**response.json())

    assert job_script.id == rows[0].id
    assert job_script.job_script_name == job_script_data["job_script_name"]
    assert job_script.job_script_owner_email == "owner1@org.com"
    assert job_script.job_script_description == ""
    assert job_script.job_script_files is None
    assert job_script.application_id is None
    assert job_script.created_at in window
    assert job_script.updated_at in window


@pytest.mark.asyncio
async def test_create_job_script_application_not_uploaded(
    synth_session,
    fill_application_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
):
    """
    Test that it is not possible to create job_script when the application is marked as not uploaded.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
            application_uploaded=False,
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.post(
        "/jobbergate/job-scripts/",
        json=fill_job_script_data(
            application_id=inserted_application_id,
            param_dict=param_dict,
        ),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
async def test_create_job_script_bad_permission(
    synth_session,
    fill_application_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
):
    """
    Test that it is not possible to create job_script without proper permission.

    This test proves that is not possible to create a job_script without the proper permission.
    We show this by trying to create a job_script without a permission that allow "create" then assert
    that the job_script still does not exists in the database, and the correct status code (403) is returned.
    and that the boto3 method is never called.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.post(
        "/jobbergate/job-scripts/",
        json=fill_job_script_data(
            application_id=inserted_application_id,
            param_dict=param_dict,
        ),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
async def test_create_job_script_without_application(
    synth_session,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
):
    """
    Test that is not possible to create a job_script without an application.

    This test proves that is not possible to create a job_script without an existing application.
    We show this by trying to create a job_script without an application created before, then assert that the
    job_script still does not exists in the database and the correct status code (404) is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)

    response = await client.post(
        "/jobbergate/job-scripts/",
        json=fill_job_script_data(application_id=9999, param_dict=param_dict),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.application_files.ApplicationFiles.get_from_s3")
async def test_create_job_script_file_not_found(
    mocked_get_application_files_from_s3,
    synth_session,
    fill_application_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
):
    """
    Test that is not possible to create a job_script if the application is in the database but not in S3.

    This test proves that is not possible to create a job_script with an existing application in the
    database but not in S3, this covers for when for some reason the application file in S3 is deleted but it
    remains in the database. We show this by trying to create a job_script with an existing application that
    is not in S3 (raises BotoCoreError), then assert that the job_script still does not exists in the
    database, the correct status code (404) is returned and that the boto3 method was called.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
            application_uploaded=False,
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    mocked_get_application_files_from_s3.return_value = ApplicationFiles()

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.post(
        "/jobbergate/job-scripts/",
        json=fill_job_script_data(
            application_id=inserted_application_id,
            param_dict=param_dict,
        ),
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
async def test_create_job_script_unable_to_write_file_to_s3(
    synth_session,
    fill_application_data,
    fill_job_script_data,
    param_dict,
    client,
    inject_security_header,
    dummy_application_config,
    dummy_application_source_file,
    dummy_template,
    mocked_file_manager_factory,
):
    """
    Test that a job script is not added to the database when S3 manager gets an error.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
            application_uploaded=False,
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    ApplicationFiles(
        templates={"test_job_script.sh": dummy_template},
        source_file=dummy_application_source_file,
        config_file=dummy_application_config,
    ).write_to_s3(inserted_application_id)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with mock.patch(
        "jobbergate_api.apps.job_scripts.job_script_files.JobScriptFiles.write_to_s3",
        side_effect=KeyError,
    ):
        response = await client.post(
            "/jobbergate/job-scripts/",
            json=fill_job_script_data(
                application_id=inserted_application_id,
                param_dict=param_dict,
            ),
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
async def test_get_job_script_by_id(
    synth_session,
    client,
    fill_application_data,
    job_script_data,
    fill_job_script_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """
    Test GET /job-scripts/<id>.

    This test proves that GET /job-scripts/<id> returns the correct job-script, owned by
    the user making the request. We show this by asserting that the job_script data
    returned in the response is equal to the job_script data that exists in the database
    for the given job_script id.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
            application_name="dummy-application",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    main_file_path = pathlib.Path("jobbergate.py")
    dummy_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: "print(__name__)"}
    )
    dummy_job_script_files.write_to_s3(inserted_job_script_id)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"/jobbergate/job-scripts/{inserted_job_script_id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_job_script_id
    assert data["job_script_name"] == job_script_data["job_script_name"]
    assert data["job_script_owner_email"] == "owner1@org.com"
    assert data["application_id"] == inserted_application_id
    assert data["application_name"] == "dummy-application"
    assert JobScriptFiles(**data["job_script_files"]) == dummy_job_script_files


@pytest.mark.asyncio
async def test_download_job_script_file_by_id__success(
    synth_session,
    client,
    fill_job_script_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """Test that a job script file can be downloaded."""
    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    main_file_path = pathlib.Path("jobbergate.py")
    expected_file_content = "print(__name__)"

    dummy_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: expected_file_content}
    )
    dummy_job_script_files.write_to_s3(inserted_job_script_id)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"/jobbergate/job-scripts/{inserted_job_script_id}/download")

    assert response.status_code == status.HTTP_200_OK

    assert response.read() == expected_file_content.encode()
    assert response.headers["filename"] == main_file_path.as_posix()


@pytest.mark.asyncio
async def test_download_job_script_file_by_id__job_script_not_found(
    synth_session,
    client,
    inject_security_header,
):
    """Test that a job script file can not be downloaded when its id is not found at the database."""
    assert await fetch_count(synth_session, job_scripts_table) == 0

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/1/download")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Could not find job_scripts instance with id 1" in response.text


@pytest.mark.asyncio
async def test_download_job_script_file_by_id__job_script_file_not_found(
    synth_session,
    client,
    fill_job_script_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """Test that a job script file can not be downloaded when its not found at s3."""
    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"/jobbergate/job-scripts/{inserted_job_script_id}/download")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Main file from job_script_id={inserted_job_script_id} was not found." in response.text


@pytest.mark.asyncio
async def test_upload_job_script_file_by_id__success(
    synth_session,
    client,
    fill_job_script_data,
    inject_security_header,
    make_dummy_file,
    time_frame,
    mocked_file_manager_factory,
):
    """Test that a job script file can be uploaded."""
    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    main_file_path = pathlib.Path("jobbergate.py")

    old_file_content = "I'm going to be replaced"
    new_file_content = "I'm the new content"

    dummy_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: old_file_content}
    )
    dummy_job_script_files.write_to_s3(inserted_job_script_id)

    new_job_script_file = make_dummy_file(main_file_path, content=new_file_content)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)

    with time_frame() as window:
        response = await client.patch(
            f"/jobbergate/job-scripts/{inserted_job_script_id}/upload",
            files={"job_script_file": open(new_job_script_file, "rb")},
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    expected_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: new_file_content}
    )
    actual_job_script_files = JobScriptFiles.get_from_s3(inserted_job_script_id)

    assert actual_job_script_files == expected_job_script_files

    job_script = await fetch_instance(
        synth_session, inserted_job_script_id, job_scripts_table, JobScriptResponse
    )
    assert job_script.updated_at in window


@pytest.mark.asyncio
async def test_upload_job_script_file_by_id__job_script_not_found(
    synth_session,
    client,
    inject_security_header,
    make_dummy_file,
):
    """Test that a job script file cannot be uploaded when its id is not found at the database."""
    assert await fetch_count(synth_session, job_scripts_table) == 0

    main_file_path = pathlib.Path("jobbergate.py")
    main_file_content = "I'm going to be replaced"

    new_job_script_file = make_dummy_file(main_file_path, content=main_file_content)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)

    response = await client.patch(
        "/jobbergate/job-scripts/1/upload",
        files={"job_script_file": open(new_job_script_file, "rb")},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Could not find job_scripts instance with id 1" in response.text


@pytest.mark.asyncio
async def test_upload_job_script_file_by_id__job_script_file_not_found(
    synth_session,
    client,
    fill_job_script_data,
    inject_security_header,
    make_dummy_file,
    mocked_file_manager_factory,
):
    """Test that a job script file can not be uploaded when its not found at s3."""
    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    main_file_path = pathlib.Path("jobbergate.py")
    new_file_content = "I'm going to be replaced"
    new_job_script_file = make_dummy_file(main_file_path, content=new_file_content)

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)

    response = await client.patch(
        f"/jobbergate/job-scripts/{inserted_job_script_id}/upload",
        files={"job_script_file": open(new_job_script_file, "rb")},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Main file from job_script_id={inserted_job_script_id} was not found." in response.text


@pytest.mark.asyncio
async def test_upload_job_script_file_by_id__fails_for_non_owner(
    synth_session,
    client,
    fill_job_script_data,
    inject_security_header,
    make_dummy_file,
):
    """Test that a job script file can not be uploaded by a non owner."""
    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(
            job_script_owner_email="owner1@org.com",
        ),
    )

    main_file_path = pathlib.Path("jobbergate.py")
    new_file_content = "I'm the new content"
    new_job_script_file = make_dummy_file(main_file_path, content=new_file_content)

    inject_security_header("non-owner@org.com", Permissions.JOB_SCRIPTS_EDIT)

    response = await client.patch(
        f"/jobbergate/job-scripts/{inserted_job_script_id}/upload",
        files={"job_script_file": open(new_job_script_file, "rb")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "does not own" in response.text


@pytest.mark.asyncio
async def test_get_job_script_by_id_file_not_found_at_s3(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """
    Test if 404 is returned if a jobscript exists in the database but the file was not found in S3.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get(f"/jobbergate/job-scripts/{inserted_job_script_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "JobScript file not found for id=" in response.text


@pytest.mark.asyncio
async def test_get_job_script_by_id_invalid(client, inject_security_header):
    """
    Test the correct response code is returned when a job_script does not exist.

    This test proves that GET /job-script/<id> returns the correct response code when the
    requested job_script does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_script requested doesn't exist (404).
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_job_script_by_id_bad_permission(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test the correct response code is returned when the user don't have the proper permission.

    This test proves that GET /job-script/<id> returns the correct response code when the
    user don't have the proper permission. We show this by asserting that the status code
    returned is what we would expect (403).
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-scripts/{inserted_job_script_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_job_scripts__no_params(
    synth_session,
    client,
    fill_application_data,
    fill_all_job_script_data,
    inject_security_header,
):
    """
    Test GET /job-scripts/ returns only job_scripts owned by the user making the request.

    This test proves that GET /job-scripts/ returns the correct job_scripts for the user making
    the request. We show this by asserting that the job_scripts returned in the response are
    only job_scripts owned by the user making the request. This test also ensures that archived
    job_scripts are not included by default.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    await synth_session.execute(
        job_scripts_table.insert(),
        fill_all_job_script_data(
            dict(
                job_script_name="js1",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=False,
            ),
            dict(
                job_script_name="js2",
                job_script_owner_email="owner999@org.com",
                application_id=inserted_application_id,
                is_archived=False,
            ),
            dict(
                job_script_name="js3",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=False,
            ),
            dict(
                job_script_name="js4",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=True,
            ),
        ),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 4

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["js1", "js3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=2,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_scripts__bad_permission(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test GET /job-scripts/ returns 403 since the user don't have the proper permission.

    This test proves that GET /job-scripts/ returns the 403 status code when the user making the request
    don't have the permission to list. We show this by asserting that the response status code is 403.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/job-scripts/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_job_scripts__with_all_param(
    synth_session,
    client,
    fill_application_data,
    fill_all_job_script_data,
    inject_security_header,
):
    """
    Test that listing job_scripts, when all=True, contains job_scripts owned by other users.

    This test proves that the user making the request can see job_scripts owned by other users.
    We show this by creating three job_scripts, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-scripts/?all=True includes all three
    job_scripts.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    await synth_session.execute(
        job_scripts_table.insert(),
        fill_all_job_script_data(
            dict(
                job_script_name="script1",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
            ),
            dict(
                job_script_name="script2",
                job_script_owner_email="owner999@org.com",
                application_id=inserted_application_id,
            ),
            dict(
                job_script_name="script3",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
            ),
        ),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["script1", "script2", "script3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_scripts__with_include_archived_param(
    synth_session,
    client,
    fill_application_data,
    fill_all_job_script_data,
    inject_security_header,
):
    """
    Test that listing job_scripts, when include_archived=True, contains archived job_scripts.

    This test proves that the user making the request can see archived job_scripts.
    We show this by creating three job_scripts, one that is archived, and two that are not.
    Assert that the response to GET /job-scripts/?include_archived=True includes all three job_scripts.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    await synth_session.execute(
        job_scripts_table.insert(),
        fill_all_job_script_data(
            dict(
                job_script_name="script1",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=False,
            ),
            dict(
                job_script_name="script2",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=True,
            ),
            dict(
                job_script_name="script3",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
                is_archived=False,
            ),
        ),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts/?include_archived=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["script1", "script2", "script3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_scripts__with_search_param(
    synth_session, client, inject_security_header, fill_application_data
):
    """
    Test that listing job scripts, when search=<search terms>, returns matches.

    This test proves that the user making the request will be shown job scripts that match the search string.
    We show this by creating job scripts and using various search queries to match against them.

    Assert that the response to GET /job_scripts?search=<search terms> includes correct matches.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    common = dict(application_id=inserted_application_id)
    await synth_session.execute(
        job_scripts_table.insert(),
        [
            dict(
                id=1,
                job_script_name="test name one",
                job_script_owner_email="one@org.com",
                job_script_description=None,
                **common,
            ),
            dict(
                id=2,
                job_script_name="test name two",
                job_script_owner_email="two@org.com",
                job_script_description=None,
                **common,
            ),
            dict(
                id=22,
                job_script_name="test name twenty-two",
                job_script_owner_email="twenty-two@org.com",
                job_script_description="a long description of this job_script",
                **common,
            ),
        ],
    )
    assert await fetch_count(synth_session, job_scripts_table) == 3

    inject_security_header("admin@org.com", Permissions.JOB_SCRIPTS_VIEW)

    response = await client.get("/jobbergate/job-scripts?all=true&search=one")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["id"] for d in results] == [1]

    response = await client.get("/jobbergate/job-scripts?all=true&search=two")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["id"] for d in results] == [2, 22]

    response = await client.get("/jobbergate/job-scripts?all=true&search=long")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["id"] for d in results] == [22]

    response = await client.get("/jobbergate/job-scripts?all=true&search=name+test")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["id"] for d in results] == [1, 2, 22]


@pytest.mark.asyncio
async def test_get_job_scripts__with_sort_params(
    synth_session,
    client,
    fill_application_data,
    inject_security_header,
):
    """
    Test that listing job_scripts with sort params returns correctly ordered matches.

    This test proves that the user making the request will be shown job_scripts sorted in the correct order
    according to the ``sort_field`` and ``sort_ascending`` parameters.
    We show this by creating job_scripts and using various sort parameters to order them.

    Assert that the response to GET /job_scripts?sort_field=<field>&sort_ascending=<bool> includes correctly
    sorted job_script.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    common = dict(
        job_script_owner_email="admin@org.com",
        application_id=inserted_application_id,
    )
    await synth_session.execute(
        job_scripts_table.insert(),
        [
            dict(
                job_script_name="Z",
                **common,
            ),
            dict(
                job_script_name="Y",
                **common,
            ),
            dict(
                job_script_name="X",
                **common,
            ),
        ],
    )
    assert await fetch_count(synth_session, job_scripts_table) == 3

    inject_security_header("admin@org.com", Permissions.JOB_SCRIPTS_VIEW)

    response = await client.get("/jobbergate/job-scripts?sort_field=id")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_script_name"] for d in results] == ["Z", "Y", "X"]

    response = await client.get("/jobbergate/job-scripts?sort_field=id&sort_ascending=false")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_script_name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-scripts?sort_field=job_script_name")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_script_name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-scripts?all=true&sort_field=job_script_data_as_string")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid sorting column requested" in response.text


@pytest.mark.asyncio
async def test_get_job_scripts__with_pagination(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test that listing job_scripts works with pagination.

    This test proves that the user making the request can see job_scripts paginated.
    We show this by creating three job_scripts and assert that the response is correctly paginated.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    await synth_session.execute(
        job_scripts_table.insert(),
        [
            fill_job_script_data(
                job_script_name=f"script{i}",
                job_script_owner_email="owner1@org.com",
                application_id=inserted_application_id,
            )
            for i in range(1, 6)
        ],
    )
    assert await fetch_count(synth_session, job_scripts_table) == 5

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)
    response = await client.get("/jobbergate/job-scripts?start=0&limit=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["script1"]

    pagination = data.get("pagination")
    assert pagination == dict(total=5, start=0, limit=1)

    response = await client.get("/jobbergate/job-scripts?start=1&limit=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["script3", "script4"]

    pagination = data.get("pagination")
    assert pagination == dict(total=5, start=1, limit=2)

    response = await client.get("/jobbergate/job-scripts?start=2&limit=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_script_name"] for d in results] == ["script5"]

    pagination = data.get("pagination")
    assert pagination == dict(total=5, start=2, limit=2)


@pytest.mark.asyncio
async def test_get_job_scripts__from_application_id(
    synth_session,
    client,
    fill_application_data,
    fill_all_job_script_data,
    inject_security_header,
):
    """
    Test listing job_scripts when from_application_id=<num> is present.

    Only the job-scripts produced from the application with id=<num> should be returned.
    """
    raw_results = await synth_session.execute(
        applications_table.insert().returning(applications_table.c.id),
        [fill_application_data(application_owner_email="owner1@org.com")] * 3,
    )
    (inserted_application_id_1, inserted_application_id_2, inserted_application_id_3) = (
        r.id for r in raw_results
    )
    assert await fetch_count(synth_session, applications_table) == 3

    await synth_session.execute(
        job_scripts_table.insert(),
        fill_all_job_script_data(
            dict(application_id=inserted_application_id_1),
            dict(application_id=inserted_application_id_1),
            dict(application_id=inserted_application_id_2),
            dict(application_id=inserted_application_id_2),
            dict(application_id=inserted_application_id_3),
            dict(application_id=inserted_application_id_3),
        ),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 6

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_VIEW)

    for application_id in [inserted_application_id_1, inserted_application_id_2, inserted_application_id_3]:
        response = await client.get(
            f"/jobbergate/job-scripts/?from_application_id={application_id}",
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        results = data.get("results")
        assert {d["application_id"] for d in results} == {application_id}, f"{application_id=}"


@pytest.mark.freeze_time
@pytest.mark.asyncio
async def test_update_job_script(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
    time_frame,
    mocked_file_manager_factory,
):
    """
    Test update job_script via PUT.

    This test proves that the job_script values are correctly updated following a PUT request to the
    /job-scripts/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the data in the database is also updated.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    main_file_path = "jobbergate.py"
    main_file_content = "print(__name__)"
    dummy_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: main_file_content}
    )

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with time_frame() as window:
        response = await client.put(
            f"/jobbergate/job-scripts/{inserted_job_script_id}",
            json={
                "job_script_name": "new name",
                "job_script_description": "new description",
                "job_script_files": {
                    "main_file_path": main_file_path,
                    "files": {main_file_path: main_file_content},
                },
                "is_archived": True,
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["job_script_name"] == "new name"
    assert data["job_script_description"] == "new description"
    assert JobScriptFiles(**data["job_script_files"]) == dummy_job_script_files
    assert JobScriptFiles.get_from_s3(inserted_job_script_id) == dummy_job_script_files
    assert data["id"] == inserted_job_script_id
    assert data["is_archived"] is True

    job_script = await fetch_instance(
        synth_session, inserted_job_script_id, job_scripts_table, JobScriptResponse
    )
    assert job_script is not None
    assert job_script.job_script_name == "new name"
    assert job_script.job_script_description == "new description"
    assert job_script.updated_at in window
    assert job_script.is_archived


@pytest.mark.asyncio
async def test_update_job_script_not_found(
    client,
    inject_security_header,
):
    """
    Test that it is not possible to update a job_script not found.

    This test proves that it is not possible to update a job_script if it is not found. We show this by
    asserting that the response status code of the request is 404.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.put("/jobbergate/job-scripts/123", json={"job_script_name": "new name"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_job_script_unable_to_write_file_to_s3(
    synth_session,
    fill_application_data,
    fill_job_script_data,
    client,
    inject_security_header,
    mocked_file_manager_factory,
):
    """
    Test that a job script is not updated to the database when S3 manager gets an error.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with mock.patch(
        "jobbergate_api.apps.job_scripts.job_script_files.JobScriptFiles.write_to_s3",
        side_effect=KeyError,
    ):
        response = await client.put(
            f"/jobbergate/job-scripts/{inserted_job_script_id}",
            json={
                "job_script_name": "new name",
                "job_script_description": "new description",
                "job_script_data_as_string": "new value",
            },
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found in S3" in response.text


@pytest.mark.asyncio
async def test_update_job_script_bad_permission(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test that it is not possible to update a job_script if the user don't have the proper permission.

    This test proves that it is not possible to update a job_script if the user don't have permission. We
    show this by asserting that the response status code of the request is 403, and that the data stored in
    the database for the job_script is not updated.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(job_script_name="target-js", application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.put("/jobbergate/job-scripts/1", data={"job_script_name": "new name"})

    assert response.status_code == status.HTTP_403_FORBIDDEN

    job_script = await fetch_instance(
        synth_session, inserted_job_script_id, job_scripts_table, JobScriptResponse
    )
    assert job_script is not None
    assert job_script.job_script_name == "target-js"


@pytest.mark.asyncio
async def test_update_job_script_non_owner(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test that it is not possible to update a job_script if the user is not the owner.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(
            application_owner_email="owner1@org.com",
        ),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(job_script_name="target-js", application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("non-owner@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.put(
        f"/jobbergate/job-scripts/{inserted_job_script_id}", json={"job_script_name": "new name"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "does not own" in response.text


@pytest.mark.asyncio
async def test_delete_job_script(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test delete job_script via DELETE.

    This test proves that a job_script is successfully deleted via a DELETE request to the /job-scripts/<id>
    endpoint. We show this by asserting that the job_script no longer exists in the database after the
    request is made and the correct status code is returned (204).
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    with mock.patch(
        "jobbergate_api.apps.job_scripts.job_script_files.JobScriptFiles.delete_from_s3",
    ) as mocked_delete:
        inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
        response = await client.delete(f"/jobbergate/job-scripts/{inserted_job_script_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    mocked_delete.assert_called_once()

    assert await fetch_count(synth_session, job_scripts_table) == 0


@pytest.mark.asyncio
async def test_delete_job_script_not_found(client, inject_security_header):
    """
    Test that it is not possible to delete a job_script that is not found.

    This test proves that it is not possible to delete a job_script if it does not exists. We show this by
    assert that a 404 response status code is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.delete("/jobbergate/job-scripts/9999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_job_script_bad_permission(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test that it is not possible to delete a job_script when the user don't have the permission.

    This test proves that it is not possible to delete a job_script if the user don't have the permission.
    We show this by assert that a 403 response status code is returned and the job_script still exists in
    the database after the request.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/job-scripts/{inserted_job_script_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert await fetch_count(synth_session, job_scripts_table) == 1


@pytest.mark.asyncio
async def test_delete_job_script_non_owner(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    inject_security_header,
):
    """
    Test that it is not possible to delete a job_script when the user is not the owner.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    inject_security_header("non-owner@org.com", Permissions.JOB_SCRIPTS_EDIT)
    response = await client.delete(f"/jobbergate/job-scripts/{inserted_job_script_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "does not own" in response.text


@pytest.mark.asyncio
async def test_delete_job_script__unlinks_job_submissions(
    synth_session,
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test DELETE /job_scripts/<id> correctly deletes a job_script linked to a job_submission.

    Test that a the job_script_id field for connected job_submissions is set to null.
    """
    inserted_application_id = await insert_data(
        synth_session,
        applications_table,
        fill_application_data(),
    )
    assert await fetch_count(synth_session, applications_table) == 1

    inserted_job_script_id = await insert_data(
        synth_session,
        job_scripts_table,
        fill_job_script_data(application_id=inserted_application_id),
    )
    assert await fetch_count(synth_session, job_scripts_table) == 1

    await insert_data(
        synth_session,
        job_submissions_table,
        fill_job_submission_data(job_script_id=inserted_job_script_id),
    )
    assert (
        await fetch_count(
            synth_session,
            job_submissions_table,
            job_submissions_table.c.job_script_id == inserted_job_script_id,
        )
        == 1
    )

    inject_security_header("owner1@org.com", Permissions.JOB_SCRIPTS_EDIT)
    with mock.patch("jobbergate_api.apps.job_scripts.job_script_files.JobScriptFiles.delete_from_s3"):
        response = await client.delete(f"/jobbergate/job-scripts/{inserted_job_script_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    assert await fetch_count(synth_session, job_scripts_table) == 0

    assert await fetch_count(synth_session, job_submissions_table) == 1
    assert (
        await fetch_count(
            synth_session,
            job_submissions_table,
            job_submissions_table.c.job_script_id == inserted_job_script_id,
        )
        == 0
    )
