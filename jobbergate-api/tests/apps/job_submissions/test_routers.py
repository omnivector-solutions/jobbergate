"""
Tests for the /job-submissions/ endpoint.
"""
import pathlib
from unittest import mock

import pytest
from fastapi import status

from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.job_submissions.schemas import JobProperties, JobSubmissionResponse
from jobbergate_api.apps.permissions import Permissions


@pytest.mark.asyncio
async def test_create_job_submission__with_client_id_in_token(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    is pulled from the token and the created job_submission is connected to that client id.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    with mock.patch(
        "jobbergate_api.apps.job_submissions.routers.get_job_properties_from_job_script"
    ) as mocked:
        mocked.return_value = JobProperties.parse_obj(create_data["execution_parameters"])
        with time_frame() as window:
            response = await client.post("/jobbergate/job-submissions", json=create_data)
    mocked.assert_called_once_with(
        job_script_data_as_string,
        **create_data["execution_parameters"],
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert (await job_submission_service.count()) == 1

    job_submission = JobSubmissionResponse(**response.json())

    # Check that the response correspond to the entry in the database
    job_submission_raw_data = await job_submission_service.get(job_submission.id)
    assert job_submission_raw_data is not None
    assert job_submission == JobSubmissionResponse.from_orm(job_submission_raw_data)

    # Check that each field is correctly set
    assert job_submission.id == job_submission_raw_data["id"]
    assert job_submission.name == "sub1"
    assert job_submission.owner_email == "owner1@org.com"
    assert job_submission.description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.execution_directory is None
    assert job_submission.client_id == "dummy-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window

    assert job_submission.execution_parameters is not None
    assert job_submission.execution_parameters.name == "job-submission-name"
    assert job_submission.execution_parameters.comment == "I am a comment"


@pytest.mark.asyncio
async def test_create_job_submission__without_execution_parameters(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    is pulled from the token and the created job_submission is connected to that client id.

    This test is the same as the previous one, but it does not include the ``execution_parameters``
    in the payload, since they are optional.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    dummy_client_id = "dummy-cluster-client"
    inject_security_header(
        tester_email,
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id=dummy_client_id,
    )
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)

    # This test aims to prove that the execution_parameters are optional
    create_data.pop("execution_parameters", None)

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    with mock.patch(
        "jobbergate_api.apps.job_submissions.routers.get_job_properties_from_job_script"
    ) as mocked:
        mocked.return_value = JobProperties()
        with time_frame() as window:
            response = await client.post("/jobbergate/job-submissions", json=create_data)
        mocked.assert_called_once_with(inserted_job_script_id)

    assert response.status_code == status.HTTP_201_CREATED

    assert (await job_submission_service.count()) == 1

    job_submission = JobSubmissionResponse(**response.json())

    # Check that the response correspond to the entry in the database
    job_submission_raw_data = await job_submission_service.get(job_submission.id)
    assert job_submission_raw_data is not None
    assert job_submission == JobSubmissionResponse.from_orm(job_submission_raw_data)

    # Check that each field is correctly set
    assert job_submission.id == job_submission_raw_data["id"]
    assert job_submission.name == create_data.get("name")
    assert job_submission.owner_email == create_data.get("owner_email")
    assert job_submission.description == create_data.get("description")
    assert job_submission.job_script_id == create_data.get("id")
    assert job_submission.execution_directory == create_data.get("execution_directory")

    # client_id was not on the payload, it should be set by other mechanisms
    assert create_data.get("client_id") is None
    assert job_submission.client_id == dummy_client_id

    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window

    assert job_submission.execution_parameters == JobProperties().dict()


@pytest.mark.asyncio
async def test_create_job_submission__with_client_id_in_request_body(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    in the request body overrides the client id in the token.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")

    execution_parameters = {
        "name": "job-submission-name",
        "comment": "I am a comment",
    }

    with mock.patch(
        "jobbergate_api.apps.job_submissions.routers.get_job_properties_from_job_script"
    ) as mocked:
        mocked.return_value = JobProperties.parse_obj(execution_parameters)
        with time_frame() as window:
            response = await client.post(
                "/jobbergate/job-submissions",
                json=fill_job_submission_data(
                    job_script_id=inserted_job_script_id,
                    name="sub1",
                    owner_email=tester_email,
                    client_id="silly-cluster-client",
                    execution_parameters=execution_parameters,
                ),
            )

    assert response.status_code == status.HTTP_201_CREATED

    assert (await job_submission_service.count()) == 1

    job_submission = JobSubmissionResponse(**response.json())

    # Check that the response correspond to the entry in the database
    job_submission_raw_data = await job_submission_service.get(job_submission.id)
    assert job_submission_raw_data is not None
    assert job_submission == JobSubmissionResponse.from_orm(job_submission_raw_data)

    # Check that each field is correctly set
    assert job_submission.id == job_submission_raw_data["id"]
    assert job_submission.name == "sub1"
    assert job_submission.owner_email == tester_email
    assert job_submission.description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.client_id == "silly-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window

    assert job_submission.execution_parameters is not None
    assert job_submission.execution_parameters.name == "job-submission-name"
    assert job_submission.execution_parameters.comment == "I am a comment"


@pytest.mark.asyncio
async def test_create_job_submission__with_execution_directory(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission with an execution directory.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint with an attached execution directory. We show this by asserting that the job_submission is
    created in the database after the post request is made, the correct status code (201) is returned.
    We also show that the ``execution_directory`` is correctly set.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    inject_security_header(
        tester_email,
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-cluster-client",
    )
    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        execution_directory="/some/fake/path",
    )

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    with mock.patch(
        "jobbergate_api.apps.job_submissions.routers.get_job_properties_from_job_script"
    ) as mocked:
        mocked.return_value = JobProperties.parse_obj(create_data["execution_parameters"])
        with time_frame() as window:
            response = await client.post("/jobbergate/job-submissions", json=create_data)
        mocked.assert_called_once_with(
            inserted_job_script_id,
            **create_data["execution_parameters"],
        )

    assert response.status_code == status.HTTP_201_CREATED

    assert (await job_submission_service.count()) == 1

    job_submission = JobSubmissionResponse.parse_obj(response.json())

    # Check that the response correspond to the entry in the database
    job_submission_raw_data = await job_submission_service.get(job_submission.id)
    assert job_submission_raw_data is not None
    assert job_submission == JobSubmissionResponse.from_orm(job_submission_raw_data)

    assert job_submission.id == job_submission_raw_data["id"]
    assert job_submission.name == "sub1"
    assert job_submission.owner_email == "owner1@org.com"
    assert job_submission.description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.execution_directory == pathlib.Path("/some/fake/path")
    assert job_submission.client_id == "dummy-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window

    assert job_submission.execution_parameters is not None
    assert job_submission.execution_parameters.name == "job-submission-name"
    assert job_submission.execution_parameters.comment == "I am a comment"


@pytest.mark.asyncio
async def test_create_job_submission_without_job_script(
    client,
    fill_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that is not possible to create a job_submission without a job_script.

    This test proves that is not possible to create a job_submission without an existing job_script.
    We show this by trying to create a job_submission without a job_script created before, then assert that
    the job_submission still does not exists in the database, the correct status code (404) is returned.
    """
    assert (await job_submission_service.count()) == 0

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.post(
        "/jobbergate/job-submissions", json=fill_job_submission_data(job_script_id=9999)
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    assert (await job_submission_service.count()) == 0


@pytest.mark.asyncio
async def test_create_job_submission_bad_permission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test that is not possible to create a job_submission without the permission.

    This test proves that is not possible to create a job_submission using a user without the permission.
    We show this by trying to create a job_submission with a user without permission, then assert that
    the job_submission still does not exists in the database and the correct status code (403) is returned.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.post(
        "/jobbergate/job-submissions",
        json=fill_job_submission_data(job_script_id=inserted_job_script_id),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert (await job_submission_service.count()) == 0


@pytest.mark.asyncio
async def test_create_job_submission_without_client_id(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    job_script_service,
    job_script_files_service,
    job_submission_service,
):
    """
    Test that it is not possible to create a job_submission without a ``client_id``.

    This test proves that it is not possible to create a job_submission without including a
    ``client_id`` in either the request body or embedded in the access token. If none are supplied,
    we assert that a 400 response is returned.k
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )
    await job_script_service.db_session.commit()

    assert (await job_submission_service.count()) == 0

    inserted_job_script_id = base_job_script.id

    inject_security_header(
        tester_email,
        Permissions.JOB_SUBMISSIONS_EDIT,
    )
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)
    create_data.pop("client_id", None)
    response = await client.post(
        "/jobbergate/job-submissions",
        json=create_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert (await job_submission_service.count()) == 0


@pytest.mark.asyncio
async def test_get_job_submission_by_id(
    client,
    tester_email,
    fill_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test GET /job-submissions/<id>.

    This test proves that GET /job-submissions/<id> returns the correct job-submission, owned by
    the user making the request. We show this by asserting that the job_submission data
    returned in the response is equal to the job_submission data that exists in the database
    for the given job_submission id.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_job_submission_id
    assert data["name"] == "test_name"
    assert data["owner_email"] == tester_email
    assert data["job_script_id"] is None

    assert data["execution_parameters"]["name"] == "job-submission-name"
    assert data["execution_parameters"]["comment"] == "I am a comment"


@pytest.mark.asyncio
async def test_get_job_submission_by_id_bad_permission(
    client,
    tester_email,
    fill_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test the correct response code is returned when the user don't have the proper permission.

    This test proves that GET /job-submissions/<id> returns the correct response code when the user don't
    have proper permission. We show this by asserting that the status code returned is 403.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_job_submission_by_id_invalid(client, inject_security_header):
    """
    Test the correct response code is returned when a job_submission does not exist.

    This test proves that GET /job-submissions/<id> returns the correct response code when the
    requested job_submission does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_submission requested doesn't exist (404).
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_job_submissions__no_param(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test GET /job-submissions/ returns only job_submissions owned by the user making the request.

    This test proves that GET /job-submissions/ returns the correct job_submissions for the user making
    the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions owned by the user making the request.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    await database.execute_many(
        query=job_submissions_table.insert(),
        values=fill_all_job_submission_data(
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub1",
                job_submission_owner_email="owner1@org.com",
                execution_parameters={
                    "name": "job-submission-name-1",
                    "comment": "I am a comment",
                },
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="owner999@org.com",
                execution_parameters={
                    "name": "job-submission-name-2",
                    "comment": "I am a comment",
                },
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="owner1@org.com",
                execution_parameters={
                    "name": "job-submission-name-3",
                    "comment": "I am a comment",
                },
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub1", "sub3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=2,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_submissions__bad_permission(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test GET /job-submissions/ returns 403 for a user without permission.

    This test proves that GET /job-submissions/ returns the correct status code (403) for a user without
    permission. We show this by asserting that the status code of the response is 403.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/job-submissions")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_job_submissions__with_all_param(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that listing job_submissions, when all=True, contains job_submissions owned by other users.

    This test proves that the user making the request can see job_submissions owned by other users.
    We show this by creating three job_submissions, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-submissions/?all=True includes all three
    job_submissions.
    """
    submission_list = fill_all_job_submission_data(
        dict(
            name="sub1",
            owner_email="owner1@org.com",
            execution_parameters={
                "name": "job-submission-name-1",
                "comment": "I am a comment",
            },
        ),
        dict(
            name="sub2",
            owner_email="owner999@org.com",
            execution_parameters={
                "name": "job-submission-name-2",
                "comment": "I am a comment",
            },
        ),
        dict(
            name="sub3",
            owner_email="owner1@org.com",
            execution_parameters={
                "name": "job-submission-name-3",
                "comment": "I am a comment",
            },
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub1", "sub2", "sub3"]

    assert data["total"] == len(submission_list)
    assert data["page"] == 1
    assert data["size"] == 50
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_get_job_submissions__from_job_script_id(
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    job_script_service,
    job_submission_service,
):
    """
    Test listing job-submissions when from_job_script_id=<num> is present.

    Only the job-submissions produced from the job-script with id=<num> should be returned.
    """

    job_script_list = [await job_script_service.create(**fill_job_script_data()) for _ in range(3)]

    submission_list = fill_all_job_submission_data(
        {"job_script_id": job_script_list[0].id},
        {"job_script_id": job_script_list[0].id},
        {"job_script_id": job_script_list[1].id},
        {"job_script_id": job_script_list[1].id},
        {"job_script_id": job_script_list[2].id},
        {"job_script_id": job_script_list[2].id},
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    for job_script in job_script_list:
        response = await client.get(f"/jobbergate/job-submissions?from_job_script_id={job_script.id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        results = data.get("items")

        assert {d["job_script_id"] for d in results} == {job_script.id}


@pytest.mark.asyncio
async def test_get_job_submissions__with_status_param(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that listing job_submissions, when status is set, contains job_submissions with matching status.

    This test proves that job_submissions are filtered by the status parameter. We do this by setting the
    status param and making sure that only job_submissions with that status are returned.
    """

    submission_list = fill_all_job_submission_data(
        dict(
            name="sub1",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.CREATED,
        ),
        dict(
            name="sub2",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.CREATED,
        ),
        dict(
            name="sub3",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.COMPLETED,
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get(f"/jobbergate/job-submissions?submit_status={JobSubmissionStatus.CREATED}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub1", "sub2"]

    assert data["total"] == 2
    assert data["page"] == 1
    assert data["size"] == 50
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_get_job_submissions__with_search_param(
    client,
    inject_security_header,
    fill_all_job_submission_data,
    job_submission_service,
):
    """
    Test that listing job submissions, when search=<search terms>, returns matches.

    This test proves that the user making the request will be shown job submissions that match the search
    string.  We show this by creating job submissions and using various search queries to match against them.

    Assert that the response to GET /job_submissions?search=<search temrms> includes correct matches.
    """
    submission_list = fill_all_job_submission_data(
        dict(name="test name one", owner_email="one@org.com"),
        dict(name="test name two", owner_email="two@org.com"),
        dict(
            name="test name twenty-two",
            owner_email="twenty-two@org.com",
            description="a long description of this job_script",
        ),
    )
    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    response = await client.get("/jobbergate/job-submissions?all=true&search=one")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["test name one"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=two")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["test name two", "test name twenty-two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=long")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["test name twenty-two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=name+test")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == [
        "test name one",
        "test name two",
        "test name twenty-two",
    ]


@pytest.mark.asyncio
async def test_get_job_submissions_with_sort_params(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that listing job_submissions with sort params returns correctly ordered matches.

    This test proves that the user making the request will be shown job_submissions sorted in the correct
    order according to the ``sort_field`` and ``sort_ascending`` parameters.
    We show this by creating job_submissions and using various sort parameters to order them.

    Assert that the response to GET /job_submissions?sort_field=<field>&sort_ascending=<bool> includes
    correctly sorted job_submissions.
    """
    submission_list = fill_all_job_submission_data(
        dict(name="Z", owner_email="admin@org.com", status=JobSubmissionStatus.REJECTED),
        dict(name="Y", owner_email="admin@org.com", status=JobSubmissionStatus.COMPLETED),
        dict(name="X", owner_email="admin@org.com", status=JobSubmissionStatus.FAILED),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    response = await client.get("/jobbergate/job-submissions?sort_field=id")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["Z", "Y", "X"]

    response = await client.get("/jobbergate/job-submissions?sort_field=id&sort_ascending=false")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=name")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("items")
    assert [d["name"] for d in results] == ["Y", "X", "Z"]

    response = await client.get("/jobbergate/job-submissions?all=true&sort_field=description")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid sorting column requested" in response.text


@pytest.mark.asyncio
async def test_list_job_submission_pagination(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that listing job_submissions works with pagination.

    this test proves that the user making the request can see job_submisions paginated.
    We show this by creating three job_submissions and assert that the response is correctly paginated.
    """
    submission_list = fill_all_job_submission_data(
        *[
            dict(
                name=f"sub{i}",
                owner_email="owner1@org.com",
            )
            for i in range(1, 6)
        ]
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions?page=1&size=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub1"]

    assert data["total"] == 5
    assert data["page"] == 1
    assert data["size"] == 1
    assert data["pages"] == 5

    response = await client.get("/jobbergate/job-submissions?page=2&size=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub3", "sub4"]

    assert data["total"] == 5
    assert data["page"] == 2
    assert data["size"] == 2
    assert data["pages"] == 3

    response = await client.get("/jobbergate/job-submissions?page=3&size=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub5"]

    assert data["total"] == 5
    assert data["page"] == 3
    assert data["size"] == 2
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_get_job_submissions_with_slurm_job_ids_param(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test GET /job-submissions/ returns only job_submissions that have one of the supplied slurm job ids.

    This test proves that GET /job-submissions returns the correct job_submissions with matching slurm_job_id.
    We show this by asserting that the job_submissions returned in the response have one of the supplied
    slurm job ids.
    """
    submission_list = fill_all_job_submission_data(
        dict(
            name="sub1",
            owner_email="owner1@org.com",
            slurm_job_id=101,
        ),
        dict(
            name="sub2",
            owner_email="owner1@org.com",
            slurm_job_id=102,
        ),
        dict(
            name="sub3",
            owner_email="owner1@org.com",
            slurm_job_id=103,
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101,103")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("items")
    assert results
    assert [d["name"] for d in results] == ["sub1", "sub3"]

    assert data["total"] == 2
    assert data["page"] == 1
    assert data["size"] == 50
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_get_job_submissions_applies_no_slurm_filter_if_slurm_job_ids_is_empty(
    client,
    inject_security_header,
    fill_all_job_submission_data,
    job_submission_service,
):
    """
    Test GET /job-submissions/ skips filtering on slurm_job_id if the param is an empty string.

    This test proves that GET /job-submissions doesn't use the slurm_job_id filter if it is an empty string.
    We show this by asserting that passing an empty string as a parameter has no effect.
    """
    submission_list = fill_all_job_submission_data(
        dict(
            owner_email="owner1@org.com",
            slurm_job_id=101,
        ),
        dict(
            owner_email="owner1@org.com",
            slurm_job_id=102,
        ),
        dict(
            owner_email="owner1@org.com",
            slurm_job_id=103,
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    with_empty_param_response = await client.get("/jobbergate/job-submissions?slurm_job_ids=")
    assert with_empty_param_response.status_code == status.HTTP_200_OK

    without_param_response = await client.get("/jobbergate/job-submissions")
    assert without_param_response.status_code == status.HTTP_200_OK

    assert with_empty_param_response.json() == without_param_response.json()


@pytest.mark.asyncio
async def test_get_job_submissions_with_invalid_slurm_job_ids_param(
    client,
    inject_security_header,
):
    """
    Test GET /job-submissions/ returns a 422 if the slurm_job_id parameter is invalid.

    This test proves that GET /job-submissions requires the slurm_job_ids parameter to be a comma-separated
    list of integer slurm job ids.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101-103")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text

    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=one-oh-one")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text


@pytest.mark.freeze_time
@pytest.mark.asyncio
async def test_update_job_submission__basic(
    client,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    job_submission_service,
):
    """
    Test update job_submission via PUT.

    This test proves that the job_submission values are correctly updated following a PUT request to the
    /job-submissions/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the data in the database is also updated.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    payload = dict(name="new name", description="new description", execution_directory="/some/fake/path")

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.put(f"/jobbergate/job-submissions/{inserted_job_submission_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["id"] == inserted_job_submission_id
    assert data["execution_directory"] == payload["execution_directory"]

    await job_submission_service.db_session.refresh(raw_db_data)
    assert JobSubmissionResponse.from_orm(raw_db_data) == JobSubmissionResponse.parse_obj(data)


@pytest.mark.asyncio
async def test_update_job_submission_not_found(client, inject_security_header):
    """
    Test that it is not possible to update a job_submission not found.

    This test proves that it is not possible to update a job_submission if it is not found. We show this by
    asserting that the response status code of the request is 404.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.put("/jobbergate/job-submissions/9999", json=dict(job_submission_name="new name"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_job_submission_bad_permission(
    client,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    job_submission_service,
):
    """
    Test that it is not possible to update a job_submission without the permission.

    This test proves that it is not possible to update a job_submission if the user don't have the permission.
    We show this by asserting that the response status code of the request is 403, and that the data stored in
    the database for the job_submission is not updated.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data(name="old name"))
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.put(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}",
        json=dict(name="new name"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    await job_submission_service.db_session.refresh(raw_db_data)

    assert raw_db_data.name == "old name"


@pytest.mark.asyncio
async def test_delete_job_submission(
    client,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    job_submission_service,
):
    """
    Test delete job_submission via DELETE.

    This test proves that a job_submission is successfully deleted via a DELETE request to the
    /job-submissions/<id> endpoint. We show this by asserting that the job_submission no longer exists in
    the database after the request is made and the correct status code is returned (204).
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert (await job_submission_service.count()) == 0


@pytest.mark.asyncio
async def test_delete_job_submission_not_found(client, inject_security_header):
    """
    Test that it is not possible to delete a job_submission that is not found.

    This test proves that it is not possible to delete a job_submission if it does not exists. We show this
    by asserting that a 404 response status code is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.delete("/jobbergate/job-submissions/9999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_job_submission_bad_permission(
    client,
    tester_email,
    fill_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test that it is not possible to delete a job_submission with an user without proper permission.

    This test proves that it is not possible to delete a job_submission if the user don't have the permission.
    We show this by asserting that a 403 response status code is returned and the job_submission still exists
    in the database after the request.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert (await job_submission_service.count()) == 1


@pytest.mark.asyncio
async def test_job_submissions_agent_pending__success(
    client,
    job_script_data_as_string,
    fill_job_script_data,
    job_script_files_service,
    fill_all_job_submission_data,
    inject_security_header,
    job_script_service,
    job_submission_service,
):
    """
    Test GET /job-submissions/agent/pending returns only job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/pending returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload. We also make sure that the response includes job_script_data_as_string,
    as it is fundamental for the integration with the agent.
    """
    base_job_script = await job_script_service.create(**fill_job_script_data())
    job_script_file_name = "entrypoint.py"

    await job_script_files_service.upsert(
        id=base_job_script.id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )

    inserted_job_script_id = base_job_script.id

    submission_list = fill_all_job_submission_data(
        dict(
            job_script_id=inserted_job_script_id,
            name="sub1",
            owner_email="email1@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="dummy-client",
            execution_parameters={
                "name": "job-submission-name-1",
                "comment": "I am a comment",
            },
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub2",
            owner_email="email2@dummy.com",
            status=JobSubmissionStatus.COMPLETED,
            client_id="dummy-client",
            execution_parameters={
                "name": "job-submission-name-2",
                "comment": "I am a comment",
            },
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub3",
            owner_email="email3@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="silly-client",
            execution_parameters={
                "name": "job-submission-name-3",
                "comment": "I am a comment",
            },
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub4",
            owner_email="email4@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="dummy-client",
            execution_parameters={
                "name": "job-submission-name-4",
                "comment": "I am a comment",
            },
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
        client_id="dummy-client",
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert sorted(i["name"] for i in data["items"]) == ["sub1", "sub4"]
    assert sorted(i["owner_email"] for i in data["items"]) == [
        "email1@dummy.com",
        "email4@dummy.com",
    ]
    assert {i["job_script"]["id"] for i in data["items"]} == {inserted_job_script_id}


@pytest.mark.asyncio
async def test_job_submissions_agent_pending__returns_400_if_token_does_not_carry_client_id(
    client,
    inject_security_header,
):
    """
    Test GET /job-submissions/agent/pending returns a 400 if the token payload does not include a client_id.

    This test proves that GET /job-submissions/agent/pending returns a 400 status if the access token used
    to query the route does not include a ``client_id``.
    """
    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "token does not contain a `client_id`" in response.text


@pytest.mark.asyncio
async def test_job_submissions_agent_update__success(
    fill_job_submission_data,
    client,
    inject_security_header,
    job_submission_service,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} correctly updates a job_submission status.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (200) is returned.
    We also show that the ``status`` column is set to the new status value.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    payload = dict(status=JobSubmissionStatus.SUBMITTED.value, slurm_job_id=111)

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}", json=payload
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_job_submission_id
    assert data["status"] == payload["status"]
    assert data["slurm_job_id"] == payload["slurm_job_id"]

    await job_submission_service.db_session.refresh(raw_db_data)
    assert JobSubmissionResponse.from_orm(raw_db_data) == JobSubmissionResponse.parse_obj(data)


@pytest.mark.asyncio
async def test_job_submissions_agent_update__job_rejected(
    fill_job_submission_data,
    client,
    inject_security_header,
    job_submission_service,
):
    """
    Test PUT /job-submissions/{job_submission_id} correctly updates a job_submission status to rejected.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (200) is returned.
    We also show that the ``status`` column is set to the new status value.
    """
    raw_db_data = await job_submission_service.create(**fill_job_submission_data())
    await job_submission_service.db_session.commit()
    inserted_job_submission_id = raw_db_data.id

    assert (await job_submission_service.count()) == 1

    payload = dict(
        status=JobSubmissionStatus.REJECTED.value,
        report_message="Job rejected by the system due to test-test",
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}", json=payload
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_job_submission_id
    assert data["status"] == payload["status"]
    assert data["slurm_job_id"] is None
    assert data["report_message"] == "Job rejected by the system due to test-test"

    await job_submission_service.db_session.refresh(raw_db_data)
    assert JobSubmissionResponse.from_orm(raw_db_data) == JobSubmissionResponse.parse_obj(data)


@pytest.mark.asyncio
async def test_job_submissions_agent_update__returns_400_if_token_does_not_carry_client_id(
    client,
    inject_security_header,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} returns 400 if client_id not in token payload.

    This test proves that PUT /job-submissions/agent/{job_submission_id} returns a 400 status if the access
    token used to query the route does not include a ``client_id``.
    """
    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.put(
        "/jobbergate/job-submissions/agent/1",
        json=dict(status=JobSubmissionStatus.SUBMITTED, slurm_job_id=111),
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "token does not contain a `client_id`" in response.text


@pytest.mark.asyncio
async def test_job_submissions_agent_active__success(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    job_submission_service,
):
    """
    Test GET /job-submissions/agent/active returns only active job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/active returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload and have a status of ``SUBMITTED``.
    """
    submission_list = fill_all_job_submission_data(
        dict(
            name="sub1",
            status=JobSubmissionStatus.CREATED,
            client_id="dummy-client",
            slurm_job_id=11,
        ),
        dict(
            name="sub2",
            status=JobSubmissionStatus.SUBMITTED,
            client_id="dummy-client",
            slurm_job_id=22,
        ),
        dict(
            name="sub3",
            status=JobSubmissionStatus.SUBMITTED,
            client_id="silly-client",
            slurm_job_id=33,
        ),
        dict(
            name="sub4",
            status=JobSubmissionStatus.SUBMITTED,
            client_id="dummy-client",
            slurm_job_id=44,
        ),
    )

    for item in submission_list:
        await job_submission_service.create(**item)
    await job_submission_service.db_session.commit()

    assert (await job_submission_service.count()) == len(submission_list)

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_VIEW, client_id="dummy-client")
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert {d["name"] for d in data["items"]} == {"sub2", "sub4"}
    assert {d["slurm_job_id"] for d in data["items"]} == {22, 44}


@pytest.mark.asyncio
async def test_job_submissions_agent_active__returns_400_if_token_does_not_carry_client_id(
    client,
    inject_security_header,
):
    """
    Test GET /job-submissions/agent/active returns a 400 if the token payload does not include a client_id.

    This test proves that GET /job-submissions/agent/active returns a 400 status if the access token used
    to query the route does not include a ``client_id``.
    """
    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
    )
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "token does not contain a `client_id`" in response.text
