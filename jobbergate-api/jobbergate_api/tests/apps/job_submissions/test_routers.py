"""
Tests for the /job-submissions/ endpoint.
"""
from datetime import datetime

import pytest
from fastapi import status

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import Application
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_scripts.schemas import JobScript
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.job_submissions.schemas import JobSubmission
from jobbergate_api.storage import database
from jobbergate_api.tests.apps.conftest import insert_objects


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission(
    job_script_data, application_data, client, job_submission_data, inject_security_header,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:create")
    response = await client.post("/jobbergate/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission_without_job_script(client, job_submission_data, inject_security_header):
    """
    Test that is not possible to create a job_submission without a job_script.

    This test proves that is not possible to create a job_submission without an existing job_script.
    We show this by trying to create a job_submission without a job_script created before, then assert that
    the job_submission still does not exists in the database, the correct status code (404) is returned.
    """
    inject_security_header("owner1@org.com", "jobbergate:job-submissions:create")
    response = await client.post("/jobbergate/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission_bad_permission(
    client, job_submission_data, application_data, job_script_data, inject_security_header
):
    """
    Test that is not possible to create a job_submission without the permission.

    This test proves that is not possible to create a job_submission using a user without the permission.
    We show this by trying to create a job_submission with a user without permission, then assert that
    the job_submission still does not exists in the database and the correct status code (403) is returned.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.post("/jobbergate/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission_by_id(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test GET /job-submissions/<id>.

    This test proves that GET /job-submissions/<id> returns the correct job-submission, owned by
    the user making the request. We show this by asserting that the job_submission data
    returned in the response is equal to the job_submission data that exists in the database
    for the given job_submission id.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["job_submission_name"] == job_submission_data["job_submission_name"]
    assert data["job_submission_owner_email"] == "owner1@org.com"
    assert data["job_script_id"] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission_by_id_bad_permission(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test the correct response code is returned when the user don't have the proper permission.

    This test proves that GET /job-submissions/<id> returns the correct response code when the user don't
    have proper permission. We show this by asserting that the status code returned is 403.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/job-submissions/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission_by_id_invalid(client, inject_security_header):
    """
    Test the correct response code is returned when a job_submission does not exist.

    This test proves that GET /job-submissions/<id> returns the correct response code when the
    requested job_submission does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_submission requested doesn't exist (404).
    """
    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submissions__no_param(
    client, application_data, job_submission_data, job_script_data, inject_security_header,
):
    """
    Test GET /job-submissions/ returns only job_submissions owned by the user making the request.

    This test proves that GET /job-submissions/ returns the correct job_submissions for the user making
    the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions owned by the user making the request.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=2, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=3, job_submission_owner_email="owner1@org.com", **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["id"] for d in results] == [1, 3]

    metadata = data.get("metadata")
    assert metadata == dict(
        total=2,
        page=None,
        per_page=None,
    )


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submissions__bad_permission(
    client, application_data, job_submission_data, job_script_data, inject_security_header,
):
    """
    Test GET /job-submissions/ returns 403 for a user without permission.

    This test proves that GET /job-submissions/ returns the correct status code (403) for a user without
    permission. We show this by asserting that the status code of the response is 403.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=2, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=3, job_submission_owner_email="owner1@org.com", **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/job-submissions/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission__excludes_other_owners(
    client, application_data, job_submission_data, job_script_data, inject_security_header,
):
    """
    Test job_submission_list doesn't include job_submissions owned by other users.

    This test proves that the user making the request cannot see job_submissions owned by other users.
    We show this by creating job_submissions that are owned by another user id and assert that
    the user making the request to /job-submissions/ doesn't see any of the other user's
    job_submissions in the response, len(response.json()) == 0.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=2, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=3, job_submission_owner_email="owner999@org.com", **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results == []

    metadata = data.get("metadata")
    assert metadata == dict(
        total=0,
        page=None,
        per_page=None,
    )


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submissions__with_all_param(
    client, application_data, job_submission_data, job_script_data, inject_security_header,
):
    """
    Test that listing job_submissions, when all=True, contains job_submissions owned by other users.

    This test proves that the user making the request can see job_submissions owned by other users.
    We show this by creating three job_submissions, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-submissions/?all=True includes all three
    job_submissions.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=2, job_submission_owner_email="owner999@org.com", **job_submission_data),
        JobSubmission(id=3, job_submission_owner_email="owner999@org.com", **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["id"] for d in results] == [1, 2, 3]

    metadata = data.get("metadata")
    assert metadata == dict(
        total=3,
        page=None,
        per_page=None,
    )


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_submission_pagination(
    client, application_data, job_submission_data, job_script_data, inject_security_header,
):
    """
    Test that listing job_submissions works with pagination.

    this test proves that the user making the request can see job_submisions paginated.
    We show this by creating three job_submissions and assert that the response is correctly paginated.
    """
    applications = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(applications, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=2, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=3, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=4, job_submission_owner_email="owner1@org.com", **job_submission_data),
        JobSubmission(id=5, job_submission_owner_email="owner1@org.com", **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 5

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:read")
    response = await client.get("/jobbergate/job-submissions/?page=0&per_page=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["id"] for d in results] == [1]

    metadata = data.get("metadata")
    assert metadata == dict(
        total=5,
        page=0,
        per_page=1,
    )

    response = await client.get("/jobbergate/job-submissions/?page=1&per_page=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["id"] for d in results] == [3, 4]

    metadata = data.get("metadata")
    assert metadata == dict(
        total=5,
        page=1,
        per_page=2,
    )

    response = await client.get("/jobbergate/job-submissions/?page=2&per_page=2")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["id"] for d in results] == [5]

    metadata = data.get("metadata")
    assert metadata == dict(
        total=5,
        page=2,
        per_page=2,
    )


@pytest.mark.freeze_time
@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_job_submission(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test update job_submission via PUT.

    This test proves that the job_submission values are correctly updated following a PUT request to the
    /job-submissions/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the data in the database is also updated.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:update")
    response = await client.put(
        "/jobbergate/job-submissions/1",
        data={"job_submission_name": "new name", "job_submission_description": "new description"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    now = datetime.now()

    assert data["job_submission_name"] == "new name"
    assert data["job_submission_description"] == "new description"
    assert data["id"] == 1
    assert data["updated_at"] == now.isoformat()

    query = job_submissions_table.select(job_submissions_table.c.id == 1)
    job_submission = JobSubmission.parse_obj(await database.fetch_one(query))

    assert job_submission is not None
    assert job_submission.job_submission_name == "new name"
    assert job_submission.job_submission_description == "new description"
    assert job_submission.updated_at == now


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_job_submission_not_found(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test that it is not possible to update a job_submission not found.

    This test proves that it is not possible to update a job_submission if it is not found. We show this by
    asserting that the response status code of the request is 404, and that the data stored in the
    database for the job_submission is not updated.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:update")
    response = await client.put("/jobbergate/job-submissions/123", data={"job_submission_name": "new name"})

    assert response.status_code == status.HTTP_404_NOT_FOUND

    query = job_submissions_table.select(job_submissions_table.c.id == 1)
    job_submission = JobSubmission.parse_obj(await database.fetch_one(query))

    assert job_submission is not None
    assert job_submission.job_submission_name == job_submission_data["job_submission_name"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_update_job_submission_bad_permission(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test that it is not possible to update a job_submission without the permission.

    This test proves that it is not possible to update a job_submission if the user don't have the permission.
    We show this by asserting that the response status code of the request is 403, and that the data stored in
    the database for the job_submission is not updated.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.put("/jobbergate/job-submissions/1", data={"job_submission_name": "new name"})

    assert response.status_code == status.HTTP_403_FORBIDDEN

    query = job_submissions_table.select(job_submissions_table.c.id == 1)
    job_submission = JobSubmission.parse_obj(await database.fetch_one(query))

    assert job_submission is not None
    assert job_submission.job_submission_name == job_submission_data["job_submission_name"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_job_submission(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test delete job_submission via DELETE.

    This test proves that a job_submission is successfully deleted via a DELETE request to the
    /job-submissions/<id> endpoint. We show this by asserting that the job_submission no longer exists in
    the database after the request is made and the correct status code is returned (204).
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:delete")
    response = await client.delete("/jobbergate/job-submissions/1")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_job_submission_not_found(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test that it is not possible to delete a job_submission that is not found.

    This test proves that it is not possible to delete a job_submission if it does not exists. We show this
    by asserting that a 404 response status code is returned and the job_submission still exists in the
    database after the request.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "jobbergate:job-submissions:delete")
    response = await client.delete("/jobbergate/job-submissions/123")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_delete_job_submission_bad_permission(
    client, application_data, job_script_data, job_submission_data, inject_security_header,
):
    """
    Test that it is not possible to delete a job_submission with an user without proper permission.

    This test proves that it is not possible to delete a job_submission if the user don't have the permission.
    We show this by asserting that a 403 response status code is returned and the job_submission still exists
    in the database after the request.
    """
    application = [Application(id=1, application_owner_email="owner1@org.com", **application_data)]
    await insert_objects(application, applications_table)

    job_scripts = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_scripts, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_email="owner1@org.com", **job_submission_data)
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.delete("/jobbergate/job-submissions/1")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1
