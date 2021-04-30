"""
Tests for the /job-submissions/ endpoint.
"""
import nest_asyncio
import pytest
from fastapi import status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_scripts.schemas import JobScript
from jobbergateapi2.apps.job_submissions.models import job_submissions_table
from jobbergateapi2.apps.job_submissions.schemas import JobSubmission
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import UserCreate
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects

# because the http test client runs an event loop fot itself,
# this lib is necessary to avoid the errror "this event loop
# is already running"
nest_asyncio.apply()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission(
    job_script_data, application_data, client, user_data, job_submission_data
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)
    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)
    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    response = client.post("/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_201_CREATED

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission_without_job_script(client, user_data, job_submission_data):
    """
    Test that is not possible to create a job_submission without a job_script.

    This test proves that is not possible to create a job_submission without an existing job_script.
    We show this by trying to create a job_submission without a job_script created before, then assert that
    the job_submission still does not exists in the database, the correct status code (404) is returned.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.post("/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_create_job_submission_wrong_user(
    job_script_data, application_data, client, user_data, job_submission_data
):
    """
    Test that it is not possible to create a job_submission using a job_script owned by another user.

    This test proves that is not possible to create a job_submission with another user's job_script.
    We show this by trying to create a job_submission with a job_script from another user (id=999), then
    assert that the job_submission still does not exists in the database, the correct status code (404) is
    returned.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)
    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)
    job_script_data["job_script_owner_id"] = 999
    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    response = client.post("/job-submissions/", json=job_submission_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission_by_id(
    client, user_data, application_data, job_script_data, job_submission_data
):
    """
    Test GET /job-submissions/<id>.

    This test proves that GET /job-submissions/<id> returns the correct job-submission, owned by
    the user making the request. We show this by asserting that the job_submission data
    returned in the response is equal to the job_submission data that exists in the database
    for the given job_submission id.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [JobSubmission(id=1, job_submission_owner_id=1, **job_submission_data)]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 1

    response = client.get("/job-submissions/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["job_submission_name"] == job_submission_data["job_submission_name"]
    assert data["job_submission_owner_id"] == 1
    assert data["job_script_id"] == 1


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_job_submission_by_id_invalid(client, user_data):
    """
    Test the correct response code is returned when a job_submission does not exist.

    This test proves that GET /job-submissions/<id> returns the correct response code when the
    requested job_submission does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_submission requested doesn't exist (404).
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    response = client.get("/job-submissions/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_submission_from_user(
    client, user_data, application_data, job_submission_data, job_script_data
):
    """
    Test GET /job-submissions/ returns only job_submissions owned by the user making the request.

    This test proves that GET /job-submissions/ returns the correct job_submissions for the user making
    the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions owned by the user making the request.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_id=1, **job_submission_data),
        JobSubmission(id=2, job_submission_owner_id=999, **job_submission_data),
        JobSubmission(id=3, job_submission_owner_id=1, **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    response = client.get("/job-submissions/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 3


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_submission_from_user_empty(
    client, user_data, application_data, job_submission_data, job_script_data
):
    """
    Test job_submission_list doesn't include job_submissions owned by other users.

    This test proves that the user making the request cannot see job_submissions owned by other users.
    We show this by creating job_submissions that are owned by another user id and assert that
    the user making the request to /job-submissions/ doesn't see any of the other user's
    job_submissions in the response, len(response.json()) == 0.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_id=999, **job_submission_data),
        JobSubmission(id=2, job_submission_owner_id=999, **job_submission_data),
        JobSubmission(id=3, job_submission_owner_id=999, **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    response = client.get("/job-submissions/")
    assert response.status_code == status.HTTP_200_OK

    assert len(response.json()) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_list_job_submission_all(
    client, user_data, application_data, job_submission_data, job_script_data
):
    """
    Test that listing job_submissions, when all=True, contains job_submissions owned by other users.

    This test proves that the user making the request can see job_submissions owned by other users.
    We show this by creating three job_submissions, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-submissions/?all=True includes all three
    job_submissions.
    """
    user = [UserCreate(id=1, **user_data)]
    await insert_objects(user, users_table)

    application = [Application(id=1, application_owner_id=1, **application_data)]
    await insert_objects(application, applications_table)

    job_script = [JobScript(id=1, **job_script_data)]
    await insert_objects(job_script, job_scripts_table)

    job_submissions = [
        JobSubmission(id=1, job_submission_owner_id=999, **job_submission_data),
        JobSubmission(id=2, job_submission_owner_id=999, **job_submission_data),
        JobSubmission(id=3, job_submission_owner_id=999, **job_submission_data),
    ]
    await insert_objects(job_submissions, job_submissions_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM job_submissions")
    assert count[0][0] == 3

    response = client.get("/job-submissions/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2
    assert data[2]["id"] == 3
