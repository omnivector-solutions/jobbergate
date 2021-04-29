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
    Test that is not possible to create a job_submission based in a job_script of another user.

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
