"""
Tests for the /job-submissions/ endpoint.
"""
import pathlib

import pytest
from fastapi import status

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.job_submissions.schemas import JobSubmissionResponse
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import database


@pytest.mark.asyncio
async def test_create_job_submission__with_client_id_in_token(
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    is pulled from the token and the created job_submission is connected to that client id.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    inject_security_header(
        "owner1@org.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-cluster-client",
    )
    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        job_submission_name="sub1",
        job_submission_owner_email="owner1@org.com",
    )

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    with time_frame() as window:
        response = await client.post("/jobbergate/job-submissions/", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    id_rows = await database.fetch_all("SELECT id FROM job_submissions")
    assert len(id_rows) == 1

    job_submission = JobSubmissionResponse(**response.json())
    assert job_submission.id == id_rows[0][0]
    assert job_submission.job_submission_name == "sub1"
    assert job_submission.job_submission_owner_email == "owner1@org.com"
    assert job_submission.job_submission_description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.execution_directory is None
    assert job_submission.client_id == "dummy-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window


@pytest.mark.asyncio
async def test_create_job_submission__with_client_id_in_request_body(
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    in the request body overrides the client id in the token.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    inject_security_header(
        "owner1@org.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-cluster-client",
    )
    with time_frame() as window:
        response = await client.post(
            "/jobbergate/job-submissions/",
            json=fill_job_submission_data(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub1",
                job_submission_owner_email="owner1@org.com",
                client_id="silly-cluster-client",
            ),
        )

    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    id_rows = await database.fetch_all("SELECT id FROM job_submissions")
    assert len(id_rows) == 1

    job_submission = JobSubmissionResponse(**response.json())
    assert job_submission.id == id_rows[0][0]
    assert job_submission.job_submission_name == "sub1"
    assert job_submission.job_submission_owner_email == "owner1@org.com"
    assert job_submission.job_submission_description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.client_id == "silly-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window


@pytest.mark.asyncio
async def test_create_job_submission__with_execution_directory(
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    time_frame,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission with an execution directory.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint with an attached execution directory. We show this by asserting that the job_submission is
    created in the database after the post request is made, the correct status code (201) is returned.
    We also show that the ``execution_directory`` is correctly set.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    inject_security_header(
        "owner1@org.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-cluster-client",
    )
    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        job_submission_name="sub1",
        job_submission_owner_email="owner1@org.com",
        execution_directory="/some/fake/path",
    )

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    with time_frame() as window:
        response = await client.post("/jobbergate/job-submissions/", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    id_rows = await database.fetch_all("SELECT id FROM job_submissions")
    assert len(id_rows) == 1

    job_submission = JobSubmissionResponse(**response.json())
    assert job_submission.id == id_rows[0][0]
    assert job_submission.job_submission_name == "sub1"
    assert job_submission.job_submission_owner_email == "owner1@org.com"
    assert job_submission.job_submission_description is None
    assert job_submission.job_script_id == inserted_job_script_id
    assert job_submission.execution_directory == pathlib.Path("/some/fake/path")
    assert job_submission.client_id == "dummy-cluster-client"
    assert job_submission.status == JobSubmissionStatus.CREATED
    assert job_submission.created_at in window
    assert job_submission.updated_at in window


@pytest.mark.asyncio
async def test_create_job_submission_without_job_script(
    client,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test that is not possible to create a job_submission without a job_script.

    This test proves that is not possible to create a job_submission without an existing job_script.
    We show this by trying to create a job_submission without a job_script created before, then assert that
    the job_submission still does not exists in the database, the correct status code (404) is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.post(
        "/jobbergate/job-submissions/", json=fill_job_submission_data(job_script_id=9999)
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
async def test_create_job_submission_bad_permission(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test that is not possible to create a job_submission without the permission.

    This test proves that is not possible to create a job_submission using a user without the permission.
    We show this by trying to create a job_submission with a user without permission, then assert that
    the job_submission still does not exists in the database and the correct status code (403) is returned.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.post(
        "/jobbergate/job-submissions/",
        json=fill_job_submission_data(job_script_id=inserted_job_script_id),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
async def test_create_job_submission_without_client_id(
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
):
    """
    Test that it is not possible to create a job_submission without a ``client_id``.

    This test proves that it is not possible to create a job_submission without including a
    ``client_id`` in either the request body or embedded in the access token. If none are supplied,
    we assert that a 400 response is returned.k
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    inject_security_header(
        "owner1@org.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
    )
    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        job_submission_name="sub1",
        job_submission_owner_email="owner1@org.com",
    )
    create_data.pop("client_id", None)
    response = await client.post(
        "/jobbergate/job-submissions/",
        json=create_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
async def test_get_job_submission_by_id(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test GET /job-submissions/<id>.

    This test proves that GET /job-submissions/<id> returns the correct job-submission, owned by
    the user making the request. We show this by asserting that the job_submission data
    returned in the response is equal to the job_submission data that exists in the database
    for the given job_submission id.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_name="sub1",
            job_submission_owner_email="owner1@org.com",
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_job_submission_id
    assert data["job_submission_name"] == "sub1"
    assert data["job_submission_owner_email"] == "owner1@org.com"
    assert data["job_script_id"] == inserted_job_script_id


@pytest.mark.asyncio
async def test_get_job_submission_by_id_bad_permission(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test the correct response code is returned when the user don't have the proper permission.

    This test proves that GET /job-submissions/<id> returns the correct response code when the user don't
    have proper permission. We show this by asserting that the status code returned is 403.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
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
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="owner999@org.com",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="owner1@org.com",
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions/")
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
    response = await client.get("/jobbergate/job-submissions/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_job_submissions__with_all_param(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test that listing job_submissions, when all=True, contains job_submissions owned by other users.

    This test proves that the user making the request can see job_submissions owned by other users.
    We show this by creating three job_submissions, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-submissions/?all=True includes all three
    job_submissions.
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
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="owner999@org.com",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="owner1@org.com",
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub1", "sub2", "sub3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_submissions__with_status_param(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test that listing job_submissions, when status is set, contains job_submissions with matching status.

    This test proves that job_submissions are filtered by the status parameter. We do this by setting the
    status param and making sure that only job_submissions with that status are returned.
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
                status=JobSubmissionStatus.CREATED,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="owner1@org.com",
                status=JobSubmissionStatus.CREATED,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="owner1@org.com",
                status=JobSubmissionStatus.COMPLETED,
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get(f"/jobbergate/job-submissions/?submit_status={JobSubmissionStatus.CREATED}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub1", "sub2"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=2,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_job_submissions__with_search_param(
    client,
    inject_security_header,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
):
    """
    Test that listing job submissions, when search=<search terms>, returns matches.

    This test proves that the user making the request will be shown job submissions that match the search
    string.  We show this by creating job submissions and using various search queries to match against them.

    Assert that the response to GET /job_submissions?search=<search temrms> includes correct matches.
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
                job_submission_name="test name one",
                job_submission_owner_email="one@org.com",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="test name two",
                job_submission_owner_email="two@org.com",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="test name twenty-two",
                job_submission_owner_email="twenty-two@org.com",
                job_submission_description="a long description of this job_script",
            ),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    response = await client.get("/jobbergate/job-submissions?all=true&search=one")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["test name one"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=two")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["test name two", "test name twenty-two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=long")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["test name twenty-two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=name+test")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == [
        "test name one",
        "test name two",
        "test name twenty-two",
    ]


@pytest.mark.asyncio
async def test_get_job_submissions_with_sort_params(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test that listing job_submissions with sort params returns correctly ordered matches.

    This test proves that the user making the request will be shown job_submissions sorted in the correct
    order according to the ``sort_field`` and ``sort_ascending`` parameters.
    We show this by creating job_submissions and using various sort parameters to order them.

    Assert that the response to GET /job_submissions?sort_field=<field>&sort_ascending=<bool> includes
    correctly sorted job_submissions.
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
                job_submission_name="Z",
                job_submission_owner_email="admin@org.com",
                status=JobSubmissionStatus.REJECTED,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="Y",
                job_submission_owner_email="admin@org.com",
                status=JobSubmissionStatus.COMPLETED,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="X",
                job_submission_owner_email="admin@org.com",
                status=JobSubmissionStatus.FAILED,
            ),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

    response = await client.get("/jobbergate/job-submissions?sort_field=id")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["Z", "Y", "X"]

    response = await client.get("/jobbergate/job-submissions?sort_field=id&sort_ascending=false")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=job_submission_name")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["job_submission_name"] for d in results] == ["Y", "X", "Z"]

    response = await client.get("/jobbergate/job-submissions?all=true&sort_field=job_submission_description")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid sorting column requested" in response.text


@pytest.mark.asyncio
async def test_list_job_submission_pagination(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test that listing job_submissions works with pagination.

    this test proves that the user making the request can see job_submisions paginated.
    We show this by creating three job_submissions and assert that the response is correctly paginated.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_owner_email="owner1@org.com"),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    await database.execute_many(
        query=job_submissions_table.insert(),
        values=fill_all_job_submission_data(
            *[
                dict(
                    job_submission_name=f"sub{i}",
                    job_script_id=inserted_job_script_id,
                    job_submission_owner_email="owner1@org.com",
                )
                for i in range(1, 6)
            ]
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 5

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions/?start=0&limit=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub1"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=5,
        start=0,
        limit=1,
    )

    response = await client.get("/jobbergate/job-submissions/?start=1&limit=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub3", "sub4"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=5,
        start=1,
        limit=2,
    )

    response = await client.get("/jobbergate/job-submissions/?start=2&limit=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["job_submission_name"] for d in results] == ["sub5"]

    pagination = data.get("pagination")
    assert pagination == dict(total=5, start=2, limit=2)


@pytest.mark.asyncio
async def test_get_job_submissions_with_slurm_job_ids_param(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test GET /job-submissions/ returns only job_submissions that have one of the supplied slurm job ids.

    This test proves that GET /job-submissions returns the correct job_submissions with matching slurm_job_id.
    We show this by asserting that the job_submissions returned in the response have one of the supplied
    slurm job ids.
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
                job_submission_name="sub1",
                job_script_id=inserted_job_script_id,
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=101,
            ),
            dict(
                job_submission_name="sub2",
                job_script_id=inserted_job_script_id,
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=102,
            ),
            dict(
                job_submission_name="sub3",
                job_script_id=inserted_job_script_id,
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=103,
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101,103")
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
async def test_get_job_submissions_applies_no_slurm_filter_if_slurm_job_ids_is_empty(
    client,
    inject_security_header,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
):
    """
    Test GET /job-submissions/ skips filtering on slurm_job_id if the param is an empty string.

    This test proves that GET /job-submissions doesn't use the slurm_job_id filter if it is an empty string.
    We show this by asserting that passing an empty string as a parameter has no effect.
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
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=101,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=102,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_owner_email="owner1@org.com",
                slurm_job_id=103,
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

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
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    time_frame,
):
    """
    Test update job_submission via PUT.

    This test proves that the job_submission values are correctly updated following a PUT request to the
    /job-submissions/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the data in the database is also updated.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    with time_frame() as window:
        response = await client.put(
            f"/jobbergate/job-submissions/{inserted_job_submission_id}",
            json=dict(job_submission_name="new name", job_submission_description="new description"),
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["job_submission_name"] == "new name"
    assert data["job_submission_description"] == "new description"
    assert data["id"] == inserted_job_submission_id

    query = job_submissions_table.select(job_submissions_table.c.id == inserted_job_submission_id)
    job_submission_data = await database.fetch_one(query)

    assert job_submission_data is not None
    assert job_submission_data["job_submission_name"] == "new name"
    assert job_submission_data["job_submission_description"] == "new description"
    assert job_submission_data["updated_at"] in window


@pytest.mark.freeze_time
@pytest.mark.asyncio
async def test_update_job_submission__with_execution_dir(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    time_frame,
):
    """
    Test update job_submission via PUT can set execution directory.

    This test proves that the job_submission values are correctly updated following a PUT request to the
    /job-submissions/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the execution_directory is correctly updated.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    with time_frame() as window:
        response = await client.put(
            f"/jobbergate/job-submissions/{inserted_job_submission_id}",
            json=dict(execution_directory="/some/fake/path"),
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == inserted_job_submission_id
    assert data["execution_directory"] == "/some/fake/path"

    query = job_submissions_table.select(job_submissions_table.c.id == inserted_job_submission_id)
    job_submission_data = await database.fetch_one(query)

    assert job_submission_data is not None
    assert job_submission_data["execution_directory"] == "/some/fake/path"
    assert job_submission_data["updated_at"] in window


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
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test that it is not possible to update a job_submission without the permission.

    This test proves that it is not possible to update a job_submission if the user don't have the permission.
    We show this by asserting that the response status code of the request is 403, and that the data stored in
    the database for the job_submission is not updated.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_name="old name",
            job_submission_owner_email="owner1@org.com",
        ),
    )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.put(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}",
        json=dict(job_submission_name="new name"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    query = job_submissions_table.select(job_submissions_table.c.id == inserted_job_submission_id)
    job_submission = JobSubmissionResponse.parse_obj(await database.fetch_one(query))

    assert job_submission is not None
    assert job_submission.job_submission_name == "old name"


@pytest.mark.asyncio
async def test_delete_job_submission(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test delete job_submission via DELETE.

    This test proves that a job_submission is successfully deleted via a DELETE request to the
    /job-submissions/<id> endpoint. We show this by asserting that the job_submission no longer exists in
    the database after the request is made and the correct status code is returned (204).
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


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
    fill_application_data,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
):
    """
    Test that it is not possible to delete a job_submission with an user without proper permission.

    This test proves that it is not possible to delete a job_submission if the user don't have the permission.
    We show this by asserting that a 403 response status code is returned and the job_submission still exists
    in the database after the request.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )
    inserted_job_submission_id = await database.execute(
        query=job_submissions_table.insert(),
        values=fill_job_submission_data(
            job_script_id=inserted_job_script_id,
            job_submission_owner_email="owner1@org.com",
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1


@pytest.mark.asyncio
async def test_job_submissions_agent_pending__success(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """
    Test GET /job-submissions/agent/pending returns only job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/pending returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload. We also make sure that the response includes job_script_data_as_string,
    as it is fundamental for the integration with the agent.
    """
    inserted_application_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(),
    )
    inserted_job_script_id = await database.execute(
        query=job_scripts_table.insert(),
        values=fill_job_script_data(application_id=inserted_application_id),
    )

    main_file_path = pathlib.Path("jobbergate.py")
    dummy_job_script_files = JobScriptFiles(
        main_file_path=main_file_path, files={main_file_path: "print(__name__)"}
    )
    dummy_job_script_files.write_to_s3(inserted_job_script_id)

    await database.execute_many(
        query=job_submissions_table.insert(),
        values=fill_all_job_submission_data(
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub1",
                job_submission_owner_email="email1@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="email2@dummy.com",
                status=JobSubmissionStatus.COMPLETED,
                client_id="dummy-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="email3@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="silly-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub4",
                job_submission_owner_email="email4@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 4

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
        client_id="dummy-client",
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert sorted(d["job_submission_name"] for d in data) == ["sub1", "sub4"]
    assert sorted(d["job_submission_owner_email"] for d in data) == ["email1@dummy.com", "email4@dummy.com"]
    assert [JobScriptFiles(**d["job_script_files"]) for d in data] == [dummy_job_script_files] * 2


@pytest.mark.asyncio
async def test_job_submissions_agent_pending__missing_job_script_file(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    mocked_file_manager_factory,
):
    """
    Test GET /job-submissions/agent/pending returns a 404.

    This test proves that GET /job-submissions/agent/pending returns a 404 status
    if any of the job-script files is not found. It also makes sure that the missing
    id(s) are included in the response to support debugging.
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
                job_submission_owner_email="email1@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                job_submission_owner_email="email2@dummy.com",
                status=JobSubmissionStatus.COMPLETED,
                client_id="dummy-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                job_submission_owner_email="email3@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="silly-client",
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub4",
                job_submission_owner_email="email4@dummy.com",
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 4

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
        client_id="dummy-client",
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"JobScript file(s) not found, the missing ids are: {inserted_job_script_id}" in response.text


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
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    client,
    inject_security_header,
):
    """
    Test PUT /job-submissions/{job_submission_id} correctly updates a job_submission status.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (200) is returned.
    We also show that the ``status`` column is set to the new status value.
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
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
                slurm_job_id=None,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                status=JobSubmissionStatus.COMPLETED,
                client_id="dummy-client",
                slurm_job_id=None,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                status=JobSubmissionStatus.CREATED,
                client_id="silly-client",
                slurm_job_id=None,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub4",
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
                slurm_job_id=None,
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 4

    target_job_submission = await database.fetch_one(
        query=job_submissions_table.select().where(job_submissions_table.c.job_submission_name == "sub1")
    )
    assert target_job_submission is not None
    job_submission_id = target_job_submission["id"]

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-client",
    )
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{job_submission_id}",
        json=dict(
            new_status=JobSubmissionStatus.SUBMITTED.value,
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == job_submission_id
    assert data["status"] == JobSubmissionStatus.SUBMITTED
    assert data["slurm_job_id"] == 111
    assert data["execution_directory"] is None


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
    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
    )
    response = await client.put(
        "/jobbergate/job-submissions/agent/1",
        json=dict(
            new_status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "token does not contain a `client_id`" in response.text


@pytest.mark.asyncio
async def test_job_submissions_agent_active__success(
    client,
    fill_application_data,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
):
    """
    Test GET /job-submissions/agent/active returns only active job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/active returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload and have a status of ``SUBMITTED``.
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
                status=JobSubmissionStatus.CREATED,
                client_id="dummy-client",
                slurm_job_id=11,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub2",
                status=JobSubmissionStatus.SUBMITTED,
                client_id="dummy-client",
                slurm_job_id=22,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub3",
                status=JobSubmissionStatus.SUBMITTED,
                client_id="silly-client",
                slurm_job_id=33,
            ),
            dict(
                job_script_id=inserted_job_script_id,
                job_submission_name="sub4",
                status=JobSubmissionStatus.SUBMITTED,
                client_id="dummy-client",
                slurm_job_id=44,
            ),
        ),
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 4

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_VIEW,
        client_id="dummy-client",
    )
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert [d["job_submission_name"] for d in data] == ["sub2", "sub4"]
    assert [d["slurm_job_id"] for d in data] == [22, 44]


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
