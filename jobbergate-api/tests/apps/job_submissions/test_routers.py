"""
Tests for the /job-submissions/ endpoint.
"""

import itertools
import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from textwrap import dedent
from unittest import mock

import pytest
import msgpack
from fastapi import status
from sqlalchemy import insert, select

from jobbergate_api.apps.job_submissions.constants import (
    JobSubmissionStatus,
    SlurmJobState,
    JobSubmissionMetricAggregateNames,
    JobSubmissionMetricSampleRate,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.rabbitmq_notification import rabbitmq_connect
from jobbergate_api.apps.job_submissions.models import JobSubmissionMetric, JobProgress
from jobbergate_api.apps.job_submissions.schemas import JobSubmissionMetricSchema, JobSubmissionAgentMaxTimes

# Not using the synth_session fixture in a route that needs the database is unsafe
pytest.mark.usefixtures("synth_session")


def generate_job_submission_metric_columns(base_time: int, num_rows: int = 5) -> list[tuple]:
    """
    Generate a list of JobSubmissionMetric objects for a given job_submission_id.

    For simplicity, generate a list of JobSubmissionMetric objects with random values for each field
    and all matching the same tuple (job_submission_id, node_host, step, task).
    """
    node_host = str(uuid.uuid4())
    step = random.randint(0, 100)
    task = random.randint(0, 100)
    return [
        (
            base_time + i,
            node_host,
            step,
            task,
            random.uniform(0, 5),
            random.uniform(0, 5),
            random.uniform(0, 5),
            random.randint(0, 5),
            random.uniform(0, 5),
            random.randint(0, 5),
            random.randint(0, 5),
            random.randint(0, 5),
            random.randint(0, 5),
            random.randint(0, 5),
        )
        for i in range(num_rows)
    ]


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_CREATE))
async def test_create_job_submission__on_site_submission(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    synth_session,
    synth_bucket,
    synth_services,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``status``
    is ``SUBMITTED``.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id
    slurm_job_id = 1234

    inject_security_header(tester_email, permission, client_id="dummy-cluster-client")
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id, slurm_job_id=slurm_job_id)

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    response = await client.post("/jobbergate/job-submissions", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED, f"Create failed: {response.text}"

    with synth_services.crud.job_submission.bound_session(synth_session):
        assert (await synth_services.crud.job_submission.count()) == 1

    response_data = response.json()

    # Check that each field is correctly set
    assert response_data["name"] == create_data["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == create_data["description"]
    assert response_data["job_script_id"] == inserted_job_script_id
    assert response_data["execution_directory"] is None
    assert response_data["client_id"] == "dummy-cluster-client"
    assert response_data["status"] == JobSubmissionStatus.SUBMITTED
    assert response_data["sbatch_arguments"] == ["--name foo", "--comment=bar"]


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_CREATE))
async def test_create_job_submission__with_client_id_in_token(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    synth_session,
    synth_bucket,
    synth_services,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    is pulled from the token and the created job_submission is connected to that client id.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, permission, client_id="dummy-cluster-client")
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    response = await client.post("/jobbergate/job-submissions", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED, f"Create failed: {response.text}"

    with synth_services.crud.job_submission.bound_session(synth_session):
        assert (await synth_services.crud.job_submission.count()) == 1

    response_data = response.json()

    # Check that each field is correctly set
    assert response_data["name"] == create_data["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == create_data["description"]
    assert response_data["job_script_id"] == inserted_job_script_id
    assert response_data["execution_directory"] is None
    assert response_data["client_id"] == "dummy-cluster-client"
    assert response_data["status"] == JobSubmissionStatus.CREATED
    assert response_data["sbatch_arguments"] == ["--name foo", "--comment=bar"]

    created_id = response_data["id"]

    # Make sure that the data can be retrieved with a GET request
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get(f"jobbergate/job-submissions/{created_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["name"] == create_data["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == create_data["description"]
    assert response_data["job_script_id"] == inserted_job_script_id
    assert response_data["execution_directory"] is None
    assert response_data["client_id"] == "dummy-cluster-client"
    assert response_data["status"] == JobSubmissionStatus.CREATED
    assert response_data["sbatch_arguments"] == ["--name foo", "--comment=bar"]


async def test_create_job_submission__with_client_id_in_request_body(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    synth_services,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint. We show this by asserting that the job_submission is created in the database after the post
    request is made, the correct status code (201) is returned. We also show that the ``client_id``
    in the request body overrides the client id in the token.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_CREATE, client_id="dummy-cluster-client")
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)

    # Change the client_id
    create_data["client_id"] = "silly-cluster-client"

    response = await client.post("/jobbergate/job-submissions", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED, f"Create failed: {response.text}"

    assert (await synth_services.crud.job_submission.count()) == 1

    response_data = response.json()

    # Check that each field is correctly set
    assert response_data["name"] == create_data["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == create_data["description"]
    assert response_data["job_script_id"] == inserted_job_script_id
    assert response_data["execution_directory"] is None
    assert response_data["client_id"] == "silly-cluster-client"
    assert response_data["status"] == JobSubmissionStatus.CREATED
    assert response_data["sbatch_arguments"] == ["--name foo", "--comment=bar"]


async def test_create_job_submission__with_execution_directory(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    synth_services,
):
    """
    Test POST /job-submissions/ correctly creates a job_submission with an execution directory.

    This test proves that a job_submission is successfully created via a POST request to the /job-submissions/
    endpoint with an attached execution directory. We show this by asserting that the job_submission is
    created in the database after the post request is made, the correct status code (201) is returned.
    We also show that the ``execution_directory`` is correctly set.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_CREATE, client_id="dummy-cluster-client")
    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        execution_directory="/some/fake/path",
    )

    # Removed defaults to make sure these are correctly set by other mechanisms
    create_data.pop("status", None)
    create_data.pop("client_id", None)

    response = await client.post("/jobbergate/job-submissions", json=create_data)

    assert response.status_code == status.HTTP_201_CREATED, f"Create failed: {response.text}"

    assert (await synth_services.crud.job_submission.count()) == 1

    response_data = response.json()

    # Check that each field is correctly set
    assert response_data["name"] == create_data["name"]
    assert response_data["owner_email"] == tester_email
    assert response_data["description"] == create_data["description"]
    assert response_data["job_script_id"] == inserted_job_script_id
    assert response_data["execution_directory"] == "/some/fake/path"
    assert response_data["client_id"] == "dummy-cluster-client"
    assert response_data["status"] == JobSubmissionStatus.CREATED
    assert response_data["sbatch_arguments"] == ["--name foo", "--comment=bar"]


async def test_create_job_submission_without_job_script(
    client,
    fill_job_submission_data,
    inject_security_header,
    synth_session,
):
    """
    Test that is not possible to create a job_submission without a job_script.

    This test proves that is not possible to create a job_submission without an existing job_script.
    We show this by trying to create a job_submission without a job_script created before, then assert that
    the job_submission still does not exists in the database, the correct status code (404) is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_CREATE)
    response = await client.post(
        "/jobbergate/job-submissions", json=fill_job_submission_data(job_script_id=9999)
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_create_job_submission_bad_permission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test that is not possible to create a job_submission without the permission.

    This test proves that is not possible to create a job_submission using a user without the permission.
    We show this by trying to create a job_submission with a user without permission, then assert that
    the job_submission still does not exists in the database and the correct status code (403) is returned.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id
    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.post(
        "/jobbergate/job-submissions",
        json=fill_job_submission_data(job_script_id=inserted_job_script_id),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_create_job_submission_without_client_id(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    synth_services,
):
    """
    Test that it is not possible to create a job_submission without a ``client_id``.

    This test proves that it is not possible to create a job_submission without including a
    ``client_id`` in either the request body or embedded in the access token. If none are supplied,
    we assert that a 400 response is returned.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inject_security_header(
        tester_email,
        Permissions.JOB_SUBMISSIONS_CREATE,
    )
    create_data = fill_job_submission_data(job_script_id=inserted_job_script_id)
    create_data.pop("client_id", None)
    response = await client.post(
        "/jobbergate/job-submissions",
        json=create_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_CREATE))
async def test_clone_job_submission__success(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    tester_email,
    job_script_data_as_string,
    synth_session,
    synth_services,
):
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id
    slurm_job_id = 1234

    create_data = fill_job_submission_data(
        job_script_id=inserted_job_script_id,
        slurm_job_id=slurm_job_id,
        status=JobSubmissionStatus.ABORTED,
        owner_email=tester_email,
    )
    original_instance = await synth_services.crud.job_submission.create(**create_data)

    new_owner_email = "new_" + tester_email

    inject_security_header(new_owner_email, permission)
    response = await client.post(f"/jobbergate/job-submissions/clone/{original_instance.id}")

    assert response.status_code == status.HTTP_201_CREATED, f"Clone failed: {response.text}"
    response_data = response.json()

    assert response_data["cloned_from_id"] == original_instance.id
    assert response_data["id"] != original_instance.id
    assert response_data["owner_email"] == new_owner_email
    assert response_data["status"] == JobSubmissionStatus.CREATED
    assert response_data["report_message"] is None
    assert response_data["slurm_job_id"] is None
    assert response_data["slurm_job_info"] is None
    assert response_data["slurm_job_state"] is None
    assert datetime.fromisoformat(response_data["created_at"]) > original_instance.created_at
    assert datetime.fromisoformat(response_data["updated_at"]) > original_instance.updated_at

    assert response_data["client_id"] == original_instance.client_id
    assert response_data["description"] == original_instance.description
    assert response_data["execution_directory"] == original_instance.execution_directory
    assert response_data["job_script_id"] == original_instance.job_script_id
    assert response_data["name"] == original_instance.name
    assert response_data["sbatch_arguments"] == original_instance.sbatch_arguments


async def test_clone_job_submission__fail_unauthorized(fill_job_submission_data, client, synth_services):
    original_instance = await synth_services.crud.job_submission.create(**fill_job_submission_data())

    response = await client.post(f"/jobbergate/job-submissions/clone/{original_instance.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_clone_job_submission__not_found(inject_security_header, tester_email, client, synth_services):
    assert (await synth_services.crud.job_submission.count()) == 0
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_CREATE)
    response = await client.post("/jobbergate/job-submissions/clone/0")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_clone_job_submission__no_parent_job_script(
    inject_security_header, tester_email, fill_job_submission_data, client, synth_services
):
    original_instance = await synth_services.crud.job_submission.create(**fill_job_submission_data())
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_CREATE)
    response = await client.post(f"/jobbergate/job-submissions/clone/{original_instance.id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_get_job_submission_by_id(
    permission,
    client,
    tester_email,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/<id>.

    This test proves that GET /job-submissions/<id> returns the correct job-submission, owned by
    the user making the request. We show this by asserting that the job_submission data
    returned in the response is equal to the job_submission data that exists in the database
    for the given job_submission id.
    """
    inserted_instance = await synth_services.crud.job_submission.create(**fill_job_submission_data())
    inserted_job_submission_id = inserted_instance.id

    inject_security_header(tester_email, permission)
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["id"] == inserted_job_submission_id
    assert response_data["name"] == "test_name"
    assert response_data["owner_email"] == tester_email
    assert response_data["job_script_id"] is None


async def test_get_job_submission_by_id_bad_permission(
    client,
    tester_email,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test the correct response code is returned when the user don't have the proper permission.

    This test proves that GET /job-submissions/<id> returns the correct response code when the user don't
    have proper permission. We show this by asserting that the status code returned is 403.
    """
    inserted_instance = await synth_services.crud.job_submission.create(**fill_job_submission_data())
    inserted_job_submission_id = inserted_instance.id

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_job_submission_by_id_invalid(client, inject_security_header, synth_session):
    """
    Test the correct response code is returned when a job_submission does not exist.

    This test proves that GET /job-submissions/<id> returns the correct response code when the
    requested job_submission does not exist. We show this by asserting that the status code
    returned is what we would expect given the job_submission requested doesn't exist (404).
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_job_submissions__no_param(
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_session,
    unpack_response,
    synth_services,
):
    """
    Test GET /job-submissions/ returns only job_submissions owned by the user making the request.

    This test proves that GET /job-submissions/ returns the correct job_submissions for the user making
    the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions owned by the user making the request.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    all_create_data = fill_all_job_submission_data(
        dict(
            job_script_id=inserted_job_script_id,
            name="sub1",
            owner_email="owner1@org.com",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub2",
            owner_email="owner999@org.com",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub3",
            owner_email="owner1@org.com",
        ),
    )

    for create_data in all_create_data:
        await synth_services.crud.job_submission.create(**create_data)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions")
    assert unpack_response(response, key="name", sort=True) == ["sub1", "sub2", "sub3"]


async def test_get_job_submissions__bad_permission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    job_script_data_as_string,
    inject_security_header,
    synth_session,
    synth_bucket,
    synth_services,
):
    """
    Test GET /job-submissions/ returns 403 for a user without permission.

    This test proves that GET /job-submissions/ returns the correct status code (403) for a user without
    permission. We show this by asserting that the status code of the response is 403.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=base_job_script.id,
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
        file_type="ENTRYPOINT",
    )

    inserted_job_script_id = base_job_script.id

    with synth_services.crud.job_submission.bound_session(synth_session):
        await synth_services.crud.job_submission.create(
            **fill_job_submission_data(job_script_id=inserted_job_script_id)
        )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/job-submissions")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_job_submissions__user_only(
    client,
    fill_all_job_submission_data,
    fill_job_script_data,
    inject_security_header,
    synth_session,
    unpack_response,
    synth_services,
):
    """
    Test that listing job_submissions, when user_only=True, contains job_submissions only owned by requesting user.

    This test proves that the user making the request can see job_submissions owned by other users.
    We show this by creating three job_submissions, one that are owned by the user making the request, and two
    owned by another user. Assert that the response to GET /job-submissions/?all=True includes all three
    job_submissions.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    all_create_data = fill_all_job_submission_data(
        dict(
            job_script_id=inserted_job_script_id,
            name="sub1",
            owner_email="owner1@org.com",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub2",
            owner_email="owner999@org.com",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub3",
            owner_email="owner1@org.com",
        ),
    )

    for create_data in all_create_data:
        await synth_services.crud.job_submission.create(**create_data)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions", params=dict(user_only=True))
    assert unpack_response(response, key="name", sort=True) == ["sub1", "sub3"]


async def test_get_job_submissions__from_job_script_id(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    unpack_response,
    synth_services,
):
    """
    Test listing job-submissions when from_job_script_id=<num> is present.

    Only the job-submissions produced from the job-script with id=<num> should be returned.
    """
    create_script_data = fill_job_script_data()
    job_script_list = [await synth_services.crud.job_script.create(**create_script_data) for _ in range(3)]

    for i in range(6):
        await synth_services.crud.job_submission.create(
            **fill_job_submission_data(job_script_id=job_script_list[i // 2].id)
        )

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)

    for job_script in job_script_list:
        response = await client.get(f"/jobbergate/job-submissions?from_job_script_id={job_script.id}")
        assert unpack_response(response, key="job_script_id") == [job_script.id] * 2


async def test_get_job_submissions__with_status_param(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    unpack_response,
    synth_services,
):
    """
    Test that listing job_submissions, when status is set, contains job_submissions with matching status.

    This test proves that job_submissions are filtered by the status parameter. We do this by setting the
    status param and making sure that only job_submissions with that status are returned.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            name="sub1",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.CREATED,
        ),
    )
    await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            name="sub2",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.CREATED,
        ),
    )
    await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            name="sub3",
            owner_email="owner1@org.com",
            status=JobSubmissionStatus.DONE,
        ),
    )

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get(
        "/jobbergate/job-submissions", params=dict(submit_status=JobSubmissionStatus.CREATED.value)
    )
    assert unpack_response(response, key="name", sort=True) == ["sub1", "sub2"]


async def test_get_job_submissions__with_search_param(
    client,
    inject_security_header,
    fill_job_script_data,
    fill_all_job_submission_data,
    unpack_response,
    synth_services,
):
    """
    Test that listing job submissions, when search=<search terms>, returns matches.

    This test proves that the user making the request will be shown job submissions that match the search
    string.  We show this by creating job submissions and using various search queries to match against them.

    Assert that the response to GET /job_submissions?search=<search temrms> includes correct matches.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

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
        await synth_services.crud.job_submission.create(job_script_id=inserted_job_script_id, **item)

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_READ)

    response = await client.get("/jobbergate/job-submissions?all=true&search=one")
    assert unpack_response(response, key="name") == ["test name one"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=two")
    assert unpack_response(response, key="name", sort=True) == ["test name twenty-two", "test name two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=long")
    assert unpack_response(response, key="name") == ["test name twenty-two"]

    response = await client.get("/jobbergate/job-submissions?all=true&search=name+test")
    assert unpack_response(response, key="name", sort=True) == [
        "test name one",
        "test name twenty-two",
        "test name two",
    ]


async def test_get_job_submissions_with_sort_params(
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_services,
    unpack_response,
):
    """
    Test that listing job_submissions with sort params returns correctly ordered matches.

    This test proves that the user making the request will be shown job_submissions sorted in the correct
    order according to the ``sort_field`` and ``sort_ascending`` parameters.
    We show this by creating job_submissions and using various sort parameters to order them.

    Assert that the response to GET /job_submissions?sort_field=<field>&sort_ascending=<bool> includes
    correctly sorted job_submissions.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    submission_list = fill_all_job_submission_data(
        dict(name="Z", owner_email="admin@org.com", status=JobSubmissionStatus.REJECTED),
        dict(name="Y", owner_email="admin@org.com", status=JobSubmissionStatus.DONE),
        dict(name="X", owner_email="admin@org.com", status=JobSubmissionStatus.ABORTED),
    )

    for item in submission_list:
        await synth_services.crud.job_submission.create(job_script_id=inserted_job_script_id, **item)

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_READ)

    response = await client.get("/jobbergate/job-submissions?sort_field=id")
    assert unpack_response(response, key="name") == ["Z", "Y", "X"]

    response = await client.get("/jobbergate/job-submissions?sort_field=id&sort_ascending=false")
    assert unpack_response(response, key="name") == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=name")
    assert unpack_response(response, key="name") == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?sort_field=status")
    assert unpack_response(response, key="name") == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/job-submissions?all=true&sort_field=description")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid sorting column requested" in response.text


async def test_list_job_submission_pagination(
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_services,
    unpack_response,
):
    """
    Test that listing job_submissions works with pagination.

    this test proves that the user making the request can see job_submisions paginated.
    We show this by creating three job_submissions and assert that the response is correctly paginated.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    submission_list = fill_all_job_submission_data(
        *[
            dict(
                job_script_id=inserted_job_script_id,
                name=f"sub{i}",
                owner_email="owner1@org.com",
            )
            for i in range(1, 6)
        ]
    )

    for item in submission_list:
        await synth_services.crud.job_submission.create(**item)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions?page=1&size=1&sort_field=id")
    assert unpack_response(
        response,
        key="name",
        sort=True,
        check_total=5,
        check_page=1,
        check_size=1,
        check_pages=5,
    ) == ["sub1"]

    response = await client.get("/jobbergate/job-submissions?page=2&size=2&sort_field=id")
    assert sorted(
        unpack_response(
            response,
            key="name",
            sort=True,
            check_total=5,
            check_page=2,
            check_size=2,
            check_pages=3,
        )
    ) == ["sub3", "sub4"]

    response = await client.get("/jobbergate/job-submissions?page=3&size=2&sort_field=id")
    assert unpack_response(
        response,
        key="name",
        sort=True,
        check_total=5,
        check_page=3,
        check_size=2,
        check_pages=3,
    ) == ["sub5"]


async def test_get_job_submissions_with_slurm_job_ids_param(
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_services,
    unpack_response,
):
    """
    Test GET /job-submissions/ returns only job_submissions that have one of the supplied slurm job ids.

    This test proves that GET /job-submissions returns the correct job_submissions with matching slurm_job_id.
    We show this by asserting that the job_submissions returned in the response have one of the supplied
    slurm job ids.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

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
        await synth_services.crud.job_submission.create(job_script_id=inserted_job_script_id, **item)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101,103")
    assert unpack_response(response, key="name", sort=True) == ["sub1", "sub3"]


async def test_get_job_submissions_applies_no_slurm_filter_if_slurm_job_ids_is_empty(
    client,
    inject_security_header,
    fill_job_script_data,
    fill_all_job_submission_data,
    synth_services,
):
    """
    Test GET /job-submissions/ skips filtering on slurm_job_id if the param is an empty string.

    This test proves that GET /job-submissions doesn't use the slurm_job_id filter if it is an empty string.
    We show this by asserting that passing an empty string as a parameter has no effect.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

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
        await synth_services.crud.job_submission.create(job_script_id=inserted_job_script_id, **item)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)

    with_empty_param_response = await client.get("/jobbergate/job-submissions?slurm_job_ids=")
    assert with_empty_param_response.status_code == status.HTTP_200_OK

    without_param_response = await client.get("/jobbergate/job-submissions")
    assert without_param_response.status_code == status.HTTP_200_OK

    assert with_empty_param_response.json() == without_param_response.json()


async def test_get_job_submissions_with_invalid_slurm_job_ids_param(
    client,
    inject_security_header,
    synth_session,
):
    """
    Test GET /job-submissions/ returns a 422 if the slurm_job_id parameter is invalid.

    This test proves that GET /job-submissions requires the slurm_job_ids parameter to be a comma-separated
    list of integer slurm job ids.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_READ)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101-103")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text

    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=one-oh-one")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text


@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_SUBMISSIONS_UPDATE]),
        (False, [Permissions.ADMIN]),
        (False, [Permissions.JOB_SUBMISSIONS_UPDATE, Permissions.MAINTAINER]),
    ],
)
async def test_update_job_submission__basic(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
    is_owner,
    permissions,
):
    """
    Test update job_submission via PUT.

    This test proves that the job_submission values are correctly updated following a PUT request to the
    /job-submissions/<id> endpoint. We show this by assert the response status code to 201, the response data
    corresponds to the updated data, and the data in the database is also updated.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data()
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(name="new name", description="new description", execution_directory="/some/fake/path")

    owner_email = inserted_submission.owner_email
    requester_email = owner_email if is_owner else "another_" + owner_email

    inject_security_header(requester_email, *permissions)
    response = await client.put(f"/jobbergate/job-submissions/{inserted_job_submission_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK, f"Update failed: {response.text}"
    response_data = response.json()

    assert response_data["id"] == inserted_job_submission_id
    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["execution_directory"] == payload["execution_directory"]

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.name == payload["name"]
    assert instance.description == payload["description"]
    assert instance.execution_directory == payload["execution_directory"]


async def test_update_job_submission_not_found(client, inject_security_header, synth_services):
    """
    Test that it is not possible to update a job_submission not found.

    This test proves that it is not possible to update a job_submission if it is not found. We show this by
    asserting that the response status code of the request is 404.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_UPDATE)
    response = await client.put("/jobbergate/job-submissions/9999", json=dict(job_submission_name="new name"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_update_job_submission_bad_permission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    synth_services,
):
    """
    Test that it is not possible to update a job_submission without the permission.

    This test proves that it is not possible to update a job_submission if the user don't have the permission.
    We show this by asserting that the response status code of the request is 403, and that the data stored in
    the database for the job_submission is not updated.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data(name="old name")
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.put(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}",
        json=dict(name="new name"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.name == "old name"


async def test_update_job_submission_forbidden(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    synth_services,
):
    """
    Test that it is not possible to update a job_submission from another person.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data(name="old name")
    )
    inserted_job_submission_id = inserted_submission.id

    owner_email = tester_email
    requester_email = "another_" + owner_email

    inject_security_header(requester_email, "INVALID_PERMISSION")
    response = await client.put(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}",
        json=dict(name="new name"),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.name == "old name"


@pytest.mark.parametrize(
    "is_owner, permissions",
    [
        (True, [Permissions.JOB_SUBMISSIONS_DELETE]),
        (False, [Permissions.ADMIN]),
        (False, [Permissions.JOB_SUBMISSIONS_DELETE, Permissions.MAINTAINER]),
    ],
)
async def test_delete_job_submission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
    is_owner,
    permissions,
):
    """
    Test delete job_submission via DELETE.

    This test proves that a job_submission is successfully deleted via a DELETE request to the
    /job-submissions/<id> endpoint. We show this by asserting that the job_submission no longer exists in
    the database after the request is made and the correct status code is returned (204).
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data()
    )
    inserted_job_submission_id = inserted_submission.id

    owner_email = inserted_submission.owner_email
    requester_email = owner_email if is_owner else "another_" + owner_email

    inject_security_header(requester_email, *permissions)
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    await synth_services.crud.job_submission.count() == 0


async def test_delete_job_submission_not_found(client, inject_security_header, synth_session):
    """
    Test that it is not possible to delete a job_submission that is not found.

    This test proves that it is not possible to delete a job_submission if it does not exists. We show this
    by asserting that a 404 response status code is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_DELETE)
    response = await client.delete("/jobbergate/job-submissions/9999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_job_submission_bad_permission(
    client,
    tester_email,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test that it is not possible to delete a job_submission with an user without proper permission.

    This test proves that it is not possible to delete a job_submission if the user don't have the permission.
    We show this by asserting that a 403 response status code is returned and the job_submission still exists
    in the database after the request.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data()
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header(tester_email, "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_job_submission_forbidden(
    client,
    tester_email,
    fill_job_script_data,
    fill_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test that it is not possible to delete a job_submission from another person.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data()
    )
    inserted_job_submission_id = inserted_submission.id

    owner_email = tester_email
    requester_email = "another_" + owner_email

    inject_security_header(requester_email, "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submissions_agent_pending__success(
    permission,
    client,
    job_script_data_as_string,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/agent/pending returns only job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/pending returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload. We also make sure that the response includes job_script_data_as_string,
    as it is fundamental for the integration with the agent.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id
    job_script_file_name = "entrypoint.sh"

    await synth_services.file.job_script.upsert(
        parent_id=inserted_job_script_id,
        file_type="ENTRYPOINT",
        filename=job_script_file_name,
        upload_content=job_script_data_as_string,
    )

    submission_list = fill_all_job_submission_data(
        dict(
            job_script_id=inserted_job_script_id,
            name="sub1",
            owner_email="email1@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="dummy-client",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub2",
            owner_email="email2@dummy.com",
            status=JobSubmissionStatus.DONE,
            client_id="dummy-client",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub3",
            owner_email="email3@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="silly-client",
        ),
        dict(
            job_script_id=inserted_job_script_id,
            name="sub4",
            owner_email="email4@dummy.com",
            status=JobSubmissionStatus.CREATED,
            client_id="dummy-client",
        ),
    )

    for item in submission_list:
        item["sbatch_arguments"] = f"--comment={item['name']}"
        await synth_services.crud.job_submission.create(**item)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.get("/jobbergate/job-submissions/agent/pending")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert sorted(i["name"] for i in data["items"]) == ["sub1", "sub4"]
    assert sorted(i["owner_email"] for i in data["items"]) == [
        "email1@dummy.com",
        "email4@dummy.com",
    ]
    assert [i["job_script"]["id"] for i in data["items"]] == [inserted_job_script_id] * 2
    assert [i["sbatch_arguments"] for i in data["items"]] == [i["sbatch_arguments"] for i in data["items"]]

    assert all(len(i["job_script"]["files"]) >= 1 for i in data["items"])


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
        Permissions.JOB_SUBMISSIONS_READ,
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Access token does not contain\\n  1: client_id" in response.text


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE))
async def test_job_submissions_agent_submitted__success(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test POST /job-submissions/agent/submitted correctly updates a marks a job_submission as SUBMITTED.

    This test proves that a job_submission is successfully updated via a POST request to the
    /job-submissions/submitted endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (202) is returned.
    We also show that the ``status`` column is set to SUBMITTED.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data(client_id="dummy-client")
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        slurm_job_id=111,
        slurm_job_state=SlurmJobState.RUNNING,
        slurm_job_info="Fake slurm job info",
    )

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.post("/jobbergate/job-submissions/agent/submitted", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.SUBMITTED
    assert instance.slurm_job_id == payload["slurm_job_id"]
    assert instance.slurm_job_state == payload["slurm_job_state"]
    assert instance.slurm_job_info == payload["slurm_job_info"]
    assert instance.report_message is None

    query = select(JobProgress).where(JobProgress.job_submission_id == inserted_job_submission_id)
    result = (await synth_session.execute(query)).scalars().all()
    assert len(result) == 1
    assert result[0].job_submission_id == inserted_job_submission_id
    assert result[0].slurm_job_state == SlurmJobState.RUNNING
    assert result[0].additional_info is None


async def test_job_submissions_agent_submitted__fails_if_status_is_not_CREATED(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test POST /job-submissions/agent/submitted returns a 400 if the status is not CREATED.

    This test proves that a job_submission can only be marked as SUBMITTED if it is in the CREATED status. We
    do this by asserting that the response code for such a request is a 400.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.DONE,
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        slurm_job_id=111,
        slurm_job_state=SlurmJobState.RUNNING,
        slurm_job_info="Fake slurm job info",
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="dummy-client")
    response = await client.post("/jobbergate/job-submissions/agent/submitted", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only CREATED Job Submissions can be marked as SUBMITTED" in response.text


async def test_job_submissions_agent_submitted__fails_if_token_does_not_carry_client_id(
    client,
    inject_security_header,
):
    """
    Test PUT /job-submissions/agent/submitted returns 400 if client_id not in token payload.

    This test proves that PUT /job-submissions/agent/submitted returns a 400 status if the access
    token used to query the route does not include a ``client_id``.
    """
    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE)
    response = await client.put(
        "/jobbergate/job-submissions/agent/1",
        json=dict(
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Checked expressions failed: Access token does not contain\\n  1: client_id" in response.text


async def test_job_submissions_agent_submitted__fails_if_client_id_does_not_match(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test PUT /job-submissions/agent/submitted returns 403 if the client_id does not match the job_submission.

    This test proves that PUT /job-submissions/agent/submitted returns a 403 status if the access
    token used to query the route has a ``client_id`` that does not match the one carried by the
    job_submission.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id, **fill_job_submission_data(client_id="dummy-client")
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        slurm_job_id=111,
        slurm_job_state=SlurmJobState.RUNNING,
        slurm_job_info="Fake slurm job info",
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="stupid-client")
    response = await client.post("/jobbergate/job-submissions/agent/submitted", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE))
async def test_job_submissions_agent_rejected__success(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test POST /job-submissions/agent/rejected correctly updates a marks a job_submission as REJECTED.

    This test proves that a job_submission is successfully updated via a POST request to the
    /job-submissions/rejected endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (202) is returned.
    We also show that the ``status`` column is set to REJECTED.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            slurm_job_state=None,
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        report_message="Something went wrong",
    )

    inject_security_header("who@cares.com", permission, client_id="dummy-client", organization_id="dummy-org")
    response = await client.post("/jobbergate/job-submissions/agent/rejected", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.REJECTED
    assert instance.report_message == payload["report_message"]

    query = select(JobProgress).where(JobProgress.job_submission_id == inserted_job_submission_id)
    result = (await synth_session.execute(query)).scalars().all()
    assert len(result) == 1
    assert result[0].job_submission_id == inserted_job_submission_id
    assert result[0].slurm_job_state == "REJECTED"
    assert result[0].additional_info == payload["report_message"]


@pytest.mark.flaky(max_runs=3)
async def test_job_submissions_agent_rejected__publishes_status_change_to_rabbitmq_when_enabled(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    tester_email,
):
    """
    Test POST /job-submissions/agent/rejected publishes a status change to rabbitmq.

    This test proves that when a job_submission is REJECTED, a notification is sent to rabbitmq.

    This is an unstable test that may break when run with other tests that use rabbitmq. Thus,
    it is marked flaky.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            slurm_job_state=None,
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        report_message="Something went wrong",
    )

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_UPDATE,
        client_id="dummy-client",
        organization_id="dummy-org",
    )
    response = await client.post("/jobbergate/job-submissions/agent/rejected", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    async with rabbitmq_connect(exchange_name="dummy-org", do_purge=True) as (_, queue):
        message = await queue.get(timeout=1, no_ack=True)

    assert message
    assert message.headers == dict(organization="dummy-org")
    assert json.loads(message.body.decode()) == dict(
        path=f"jobs.job_submissions.{inserted_submission.id}",
        user_email=tester_email,
        action="status",
        additional_context=dict(
            status=JobSubmissionStatus.REJECTED,
            slurm_job_state=None,
        ),
    )


async def test_job_submissions_agent_rejected__fails_if_status_is_not_CREATED(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test POST /job-submissions/agent/rejected returns a 400 if the status is not CREATED.

    This test proves that a job_submission can only be marked as REJECTED if it is in the CREATED status. We
    do this by asserting that the response code for such a request is a 400.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.DONE,
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    payload = dict(
        id=inserted_job_submission_id,
        report_message="Something went wrong",
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="dummy-client")
    response = await client.post("/jobbergate/job-submissions/agent/rejected", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only CREATED Job Submissions can be marked as REJECTED" in response.text


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE))
async def test_job_submissions_agent_update__success(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} correctly updates a job_submission.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint. We show this by asserting that the job_submission is
    updated in the database after the post request is made, the correct status code (200) is returned.
    We also show that the ``slurm_job_state`` and ``slurm_job_info`` columns are set.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    job_submission_instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert job_submission_instance.id == inserted_job_submission_id
    assert job_submission_instance.status == JobSubmissionStatus.SUBMITTED
    assert job_submission_instance.slurm_job_state == SlurmJobState.RUNNING
    assert job_submission_instance.slurm_job_info == "Dummy slurm job info"
    assert job_submission_instance.slurm_job_id == 111

    query = select(JobProgress).where(JobProgress.job_submission_id == inserted_job_submission_id)
    result = (await synth_session.execute(query)).scalars().all()
    assert len(result) == 1
    assert result[0].job_submission_id == inserted_job_submission_id
    assert result[0].slurm_job_state == SlurmJobState.RUNNING
    assert result[0].additional_info is None


@pytest.mark.parametrize(
    "slurm_job_state",
    [
        SlurmJobState.BOOT_FAIL,
        SlurmJobState.CANCELLED,
        SlurmJobState.DEADLINE,
        SlurmJobState.FAILED,
        SlurmJobState.NODE_FAIL,
        SlurmJobState.PREEMPTED,
        SlurmJobState.SPECIAL_EXIT,
        SlurmJobState.TIMEOUT,
        SlurmJobState.UNKNOWN,
    ],
)
async def test_job_submissions_agent_update__sets_aborted_status(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    slurm_job_state,
    synth_session,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} correctly sets the status to aborted.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint and that its new status is set to ABORTED if the
    slurm_job_state that is reported is one of the "abort" statuses.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=slurm_job_state,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
            slurm_job_state_reason="User cancelled",
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.ABORTED
    assert instance.slurm_job_state == slurm_job_state
    assert instance.slurm_job_info == "Dummy slurm job info"
    assert instance.slurm_job_id == 111
    assert instance.report_message == "User cancelled"

    query = select(JobProgress).where(JobProgress.job_submission_id == inserted_job_submission_id)
    result = (await synth_session.execute(query)).scalars().all()
    assert len(result) == 1
    assert result[0].job_submission_id == inserted_job_submission_id
    assert result[0].slurm_job_state == slurm_job_state
    assert result[0].additional_info == "User cancelled"


async def test_job_submissions_agent_update__sets_done_status(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} correctly sets the status to done.

    This test proves that a job_submission is successfully updated via a PUT request to the
    /job-submissions/{job_submission_id} endpoint and that its new status is set to DONE if the
    slurm_job_state that is reported is one of the "done" statuses.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.COMPLETED,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.DONE
    assert instance.slurm_job_state == SlurmJobState.COMPLETED
    assert instance.slurm_job_info == "Dummy slurm job info"
    assert instance.slurm_job_id == 111

    query = select(JobProgress).where(JobProgress.job_submission_id == inserted_job_submission_id)
    result = (await synth_session.execute(query)).scalars().all()
    assert len(result) == 1
    assert result[0].job_submission_id == inserted_job_submission_id
    assert result[0].slurm_job_state == SlurmJobState.COMPLETED
    assert result[0].additional_info is None


@pytest.mark.parametrize(
    "slurm_job_state,expected_status",
    [
        (SlurmJobState.COMPLETED, JobSubmissionStatus.DONE),
        (SlurmJobState.CANCELLED, JobSubmissionStatus.ABORTED),
    ],
)
@pytest.mark.flaky(max_runs=3)
async def test_job_submissions_agent_update__publishes_status_change_to_rabbitmq_when_enabled(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    tester_email,
    slurm_job_state,
    expected_status,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} publishes status changes to rabbitmq.

    This test proves that when a job_submission is successfully updated to a DONE or ABORTED
    status, a notification is sent to rabbitmq.

    This is an unstable test that may break when run with other tests that use rabbitmq. Thus,
    it is marked flaky.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_UPDATE,
        client_id="dummy-client",
        organization_id="dummy-org",
    )

    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=slurm_job_state,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    async with rabbitmq_connect(exchange_name="dummy-org", do_purge=True) as (_, queue):
        message = await queue.get(timeout=1, no_ack=True)

    assert message
    assert message.headers == dict(organization="dummy-org")
    assert json.loads(message.body.decode()) == dict(
        path=f"jobs.job_submissions.{inserted_submission.id}",
        user_email=tester_email,
        action="status",
        additional_context=dict(
            status=expected_status,
            slurm_job_state=slurm_job_state,
        ),
    )


async def test_job_submissions_agent_update__returns_400_if_token_does_not_carry_client_id(
    client,
    inject_security_header,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} returns 400 if client_id not in token payload.

    This test proves that PUT /job-submissions/agent/{job_submission_id} returns a 400 status if the access
    token used to query the route does not include a ``client_id``.
    """
    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE)
    response = await client.put(
        "/jobbergate/job-submissions/agent/1",
        json=dict(status=JobSubmissionStatus.SUBMITTED, slurm_job_id=111),
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Checked expressions failed: Access token does not contain\\n  1: client_id" in response.text


async def test_job_submissions_agent_update__returns_403_if_client_id_differs(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} returns 403 if client_id does not match the database.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="stupid-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_job_submissions_agent_update__returns_409_if_slurm_job_id_differs(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test PUT /job-submissions/agent/{job_submission_id} returns 409 if slurm_job_id does not match.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_UPDATE, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=222,
        ),
    )
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submissions_agent_active__success(
    permission,
    client,
    fill_job_script_data,
    fill_all_job_submission_data,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/agent/active returns only active job_submissions owned by the requesting agent.

    This test proves that GET /job-submissions/agent/active returns the correct job_submissions for the agent
    making the request. We show this by asserting that the job_submissions returned in the response are
    only job_submissions with a ``client_id`` that matches the ``client_id`` found in the request's
    token payload and have a status of ``SUBMITTED``.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

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
        await synth_services.crud.job_submission.create(job_script_id=inserted_job_script_id, **item)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_200_OK, f"Get failed: {response.text}"

    response_data = response.json()
    assert {d["name"] for d in response_data["items"]} == {"sub2", "sub4"}
    assert {d["slurm_job_id"] for d in response_data["items"]} == {22, 44}


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
        Permissions.JOB_SUBMISSIONS_READ,
    )
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Access token does not contain\\n  1: client_id" in response.text


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submissions_agent_metrics__returns_successful_request__empty_list(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/agent/metrics/{job_submission_id} returns 200 with no data.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.get(f"/jobbergate/job-submissions/agent/metrics/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"job_submission_id": inserted_job_submission_id, "max_times": []}


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submissions_agent_metrics__returns_successful_request(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test GET /job-submissions/agent/metrics/{job_submission_id} returns 200 with data.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    base_time = int(datetime.now().timestamp())

    job_metrics = generate_job_submission_metric_columns(base_time)
    query = insert(JobSubmissionMetric).values(
        [
            {
                "time": item[0],
                "job_submission_id": inserted_job_submission_id,
                "slurm_job_id": inserted_submission.slurm_job_id,
                "node_host": item[1],
                "step": item[2],
                "task": item[3],
                "cpu_frequency": item[4],
                "cpu_time": item[5],
                "cpu_utilization": item[6],
                "gpu_memory": item[7],
                "gpu_utilization": item[8],
                "page_faults": item[9],
                "memory_rss": item[10],
                "disk_read": item[11],
                "memory_virtual": item[12],
                "disk_write": item[13],
            }
            for item in job_metrics
        ]
    )
    await synth_session.execute(query)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.get(f"/jobbergate/job-submissions/agent/metrics/{inserted_job_submission_id}")
    assert response.status_code == status.HTTP_200_OK
    max_time_element = max(job_metrics, key=lambda item: item[0])
    assert response.json() == {
        "job_submission_id": inserted_job_submission_id,
        "max_times": [
            JobSubmissionAgentMaxTimes(
                max_time=max_time_element[0],
                node_host=max_time_element[1],
                step=max_time_element[2],
                task=max_time_element[3],
            ).model_dump()
        ],
    }


@pytest.mark.parametrize(
    "permission, data",
    [
        (Permissions.ADMIN, "dummy-string-data"),
        (Permissions.JOB_SUBMISSIONS_UPDATE, {"dummy": "data"}),
    ],
)
@mock.patch("jobbergate_api.apps.job_submissions.routers.validate_job_metric_upload_input")
async def test_job_submissions_agent_metrics_upload__400_uploading_invalid_data(
    mocked_validate_job_metric_upload_input,
    permission,
    data,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test PUT /job-submissions/agent/metrics/{job_submission_id} returns 400 when the input data
    is invalid.
    """
    mocked_validate_job_metric_upload_input.side_effect = ValueError("Invalid data")

    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    encoded_data = msgpack.packb(data)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/metrics/{inserted_job_submission_id}",
        content=encoded_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Invalid data"}
    mocked_validate_job_metric_upload_input.assert_called_once_with(
        data, (int, str, int, int, float, float, float, int, float, int, int, int, int, int)
    )


@pytest.mark.parametrize(
    "permission, num_rows",
    [
        (Permissions.ADMIN, 3),
        (Permissions.JOB_SUBMISSIONS_UPDATE, 8),
    ],
)
async def test_job_submissions_agent_metrics_upload__successful_request(
    permission,
    num_rows,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test PUT /job-submissions/agent/metrics/{job_submission_id} returns 204 upon a successful request.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    base_time = int(datetime.now().timestamp())
    raw_data = generate_job_submission_metric_columns(base_time, num_rows)
    encoded_data = msgpack.packb(raw_data)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/metrics/{inserted_job_submission_id}",
        content=encoded_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    query = select(JobSubmissionMetric).where(
        JobSubmissionMetric.job_submission_id == inserted_job_submission_id
    )
    result = await synth_session.execute(query)
    scalars = result.scalars()
    assert all(
        (
            scalar.time,
            scalar.node_host,
            scalar.step,
            scalar.task,
            scalar.cpu_frequency,
            scalar.cpu_time,
            scalar.cpu_utilization,
            scalar.gpu_memory,
            scalar.gpu_utilization,
            scalar.page_faults,
            scalar.memory_rss,
            scalar.disk_read,
            scalar.memory_virtual,
            scalar.disk_write,
        )
        in raw_data
        for scalar in scalars
    )


@pytest.mark.parametrize(
    "permission, num_rows",
    [
        (Permissions.ADMIN, 3),
        (Permissions.JOB_SUBMISSIONS_UPDATE, 8),
    ],
)
async def test_job_submissions_agent_metrics_upload__400_duplicated_data(
    permission,
    num_rows,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test PUT /job-submissions/agent/metrics/{job_submission_id} returns 400 when uploading
    duplicated data.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    base_time = int(datetime.now().timestamp())
    raw_data = generate_job_submission_metric_columns(base_time, num_rows)
    encoded_data = msgpack.packb(raw_data)

    query = insert(JobSubmissionMetric).values(
        [
            {
                "time": data_point[0],
                "node_host": data_point[1],
                "step": data_point[2],
                "task": data_point[3],
                "cpu_frequency": data_point[4],
                "cpu_time": data_point[5],
                "cpu_utilization": data_point[6],
                "gpu_memory": data_point[7],
                "gpu_utilization": data_point[8],
                "page_faults": data_point[9],
                "memory_rss": data_point[10],
                "disk_read": data_point[11],
                "memory_virtual": data_point[12],
                "disk_write": data_point[13],
                "job_submission_id": inserted_job_submission_id,
                "slurm_job_id": inserted_submission.slurm_job_id,
            }
            for data_point in raw_data
        ]
    )
    await synth_session.execute(query)

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/metrics/{inserted_job_submission_id}",
        content=encoded_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Failed to insert metrics"}


@pytest.mark.parametrize(
    "permission, sample_rate, node_host",
    list(
        itertools.product(
            (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ),
            map(lambda enum: enum.value, JobSubmissionMetricSampleRate),
            ("node_1", "dummy-node", None),
        )
    ),
)
@mock.patch("jobbergate_api.apps.job_submissions.routers.sa_text")
async def test_job_submissions_metrics__aggregation_by_all_nodes(
    mocked_sa_text,
    permission,
    sample_rate,
    node_host,
    client,
    inject_security_header,
    synth_session,
):
    """
    Test GET /job-submissions/{job_submission_id}/metrics returns 200.
    """
    num_rows = random.randint(1, 10)
    job_submission_id = random.randint(1, 100)
    random_hour_interval = random.randint(1, 23)

    mocked_session_execute = mock.AsyncMock()
    mocked_session_execute.return_value.fetchall = mock.Mock()

    base_time = int(datetime.now().timestamp())
    raw_data = generate_job_submission_metric_columns(base_time, num_rows)

    mocked_session_execute.return_value.fetchall.return_value = [
        JobSubmissionMetricSchema.from_iterable(data_point).model_dump(exclude=["step", "task"]).values()
        for data_point in raw_data
    ]

    if node_host is not None:
        where_statement = "WHERE job_submission_id = :job_submission_id AND node_host = :node_host"
        match sample_rate:
            case JobSubmissionMetricSampleRate.ten_seconds:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_seconds_by_node
            case JobSubmissionMetricSampleRate.one_minute:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_minute_by_node
            case JobSubmissionMetricSampleRate.ten_minutes:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_minutes_by_node
            case JobSubmissionMetricSampleRate.one_hour:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_hour_by_node
            case JobSubmissionMetricSampleRate.one_week:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_week_by_node
    else:
        where_statement = "WHERE job_submission_id = :job_submission_id"
        match sample_rate:
            case JobSubmissionMetricSampleRate.ten_seconds:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_seconds_all_nodes
            case JobSubmissionMetricSampleRate.one_minute:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_minute_all_nodes
            case JobSubmissionMetricSampleRate.ten_minutes:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_minutes_all_nodes
            case JobSubmissionMetricSampleRate.one_hour:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_hour_all_nodes
            case JobSubmissionMetricSampleRate.one_week:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_week_all_nodes

    expected_sql_query = dedent(
        f"""
        SELECT bucket,
            node_host,
            cpu_frequency,
            cpu_time,
            cpu_utilization,
            gpu_memory,
            gpu_utilization,
            page_faults,
            memory_rss,
            memory_virtual,
            disk_read,
            disk_write
        FROM {view_name}
        {where_statement}
        AND bucket >= :start_time
        AND bucket <= :end_time
        ORDER BY bucket
        """
    )

    start_time = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(hours=random_hour_interval)

    http_query_params = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_rate": sample_rate,
    }

    sql_query_params = {
        "job_submission_id": job_submission_id,
        "start_time": start_time,
        "end_time": end_time,
    }

    if node_host is not None:
        http_query_params["node"] = node_host
        sql_query_params["node_host"] = node_host

    with mock.patch.object(synth_session, "execute", mocked_session_execute):
        inject_security_header("who@cares.com", permission, client_id="dummy-client")
        response = await client.get(
            f"/jobbergate/job-submissions/{job_submission_id}/metrics", params=http_query_params
        )

    assert response.status_code == status.HTTP_200_OK
    mocked_session_execute.assert_awaited_once_with(mocked_sa_text.return_value, sql_query_params)
    mocked_session_execute.return_value.fetchall.assert_called_once_with()
    mocked_sa_text.assert_called_once_with(expected_sql_query)
    assert response.json() == [
        JobSubmissionMetricSchema.from_iterable(
            (
                data_point[0],
                data_point[1],
                # skip both task and step because the API aggregates in the node level
                # data_point[2],
                # data_point[3],
                data_point[4],
                data_point[5],
                data_point[6],
                data_point[7],
                data_point[8],
                data_point[9],
                data_point[10],
                data_point[11],
                data_point[12],
                data_point[13],
            ),
            skip_optional=True,
        ).model_dump()
        for data_point in raw_data
    ]


@pytest.mark.parametrize("permission", [Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ])
@mock.patch("jobbergate_api.apps.job_submissions.routers.sa_text")
async def test_job_submissions_metrics__start_time_less_greater_than_end_time(
    mocked_sa_text,
    permission,
    client,
    inject_security_header,
    synth_session,
):
    """
    Test GET /job-submissions/{job_submission_id}/metrics returns 400 when the start_time
    query param is greater than the end_time.
    """
    job_submission_id = random.randint(1, 100)
    random_hour_interval = random.randint(1, 23)

    mocked_session_execute = mock.AsyncMock()
    mocked_session_execute.return_value.fetchall = mock.Mock()

    end_time = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    start_time = end_time + timedelta(hours=random_hour_interval)

    http_query_params = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with mock.patch.object(synth_session, "execute", mocked_session_execute):
        inject_security_header("who@cares.com", permission, client_id="dummy-client")
        response = await client.get(
            f"/jobbergate/job-submissions/{job_submission_id}/metrics", params=http_query_params
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    mocked_session_execute.assert_not_awaited()
    mocked_session_execute.return_value.fetchall.assert_not_called()
    mocked_sa_text.assert_not_called()
    assert response.json() == {"detail": "End time must be greater than the start time."}


@pytest.mark.parametrize(
    "permission, num_rows",
    [
        (Permissions.ADMIN, 3),
        (Permissions.JOB_SUBMISSIONS_READ, 8),
    ],
)
async def test_job_submissions_metrics_timestamps__successful_request(
    permission,
    num_rows,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
    synth_session,
):
    """
    Test GET /job-submissions/{job_submission_id}/metrics/timestamps returns 200 upon a successful request.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    base_time = int(datetime.now().timestamp())
    raw_data = generate_job_submission_metric_columns(base_time, num_rows)

    formatted_data = [
        {
            "time": data_point[0],
            "node_host": data_point[1],
            "step": data_point[2],
            "task": data_point[3],
            "cpu_frequency": data_point[4],
            "cpu_time": data_point[5],
            "cpu_utilization": data_point[6],
            "gpu_memory": data_point[7],
            "gpu_utilization": data_point[8],
            "page_faults": data_point[9],
            "memory_rss": data_point[10],
            "disk_read": data_point[11],
            "memory_virtual": data_point[12],
            "disk_write": data_point[13],
            "job_submission_id": inserted_job_submission_id,
            "slurm_job_id": inserted_submission.slurm_job_id,
        }
        for data_point in raw_data
    ]

    query = insert(JobSubmissionMetric).values(formatted_data)
    await synth_session.execute(query)

    inject_security_header("who@cares.com", permission)
    response = await client.get(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}/metrics/timestamps"
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == {
        "max": max(formatted_data, key=lambda x: x["time"])["time"],
        "min": min(formatted_data, key=lambda x: x["time"])["time"],
    }


@pytest.mark.parametrize(
    "permission, job_submission_id",
    [
        (Permissions.ADMIN, 64537),
        (Permissions.JOB_SUBMISSIONS_READ, 4967),
    ],
)
async def test_job_submissions_metrics_timestamps__job_submission_not_found(
    permission,
    job_submission_id,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/metrics/timestamps returns 404
    when the job submission doesn't exist
    """

    inject_security_header("who@cares.com", permission)
    response = await client.get(f"/jobbergate/job-submissions/{job_submission_id}/metrics/timestamps")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response_data = response.json()
    assert (
        response_data["detail"]
        == f"No metrics found for job submission {job_submission_id} or job submission does not exist"
    )


@pytest.mark.parametrize(
    "permission",
    [Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ],
)
async def test_job_submissions_metrics_timestamps__job_submission_has_no_metric(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/metrics/timestamps returns 404 when
    the job submission exists but has no metrics.
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    inject_security_header("who@cares.com", permission, client_id="dummy-client")
    response = await client.get(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}/metrics/timestamps"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response_data = response.json()
    assert (
        response_data["detail"]
        == f"No metrics found for job submission {inserted_job_submission_id} or job submission does not exist"
    )


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submission_progress__success(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/progress returns progress entries.

    This test proves that progress entries for a job submission can be retrieved via a GET request
    to the /job-submissions/{job_submission_id}/progress endpoint. We show this by:
    1. Creating a job script and submission
    2. Adding progress entries with different timestamps and states
    3. Retrieving the progress entries and verifying they are returned in the correct order
    """
    # Create a job script and submission
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())
    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    # Create progress entries with different timestamps and states
    progress_entries = [
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=30),
            "slurm_job_state": SlurmJobState.PENDING,
            "additional_info": "Job is pending",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=20),
            "slurm_job_state": SlurmJobState.RUNNING,
            "additional_info": "Job is running",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
            "slurm_job_state": SlurmJobState.COMPLETED,
            "additional_info": "Job completed successfully",
        },
    ]

    for entry in progress_entries:
        await synth_services.crud.job_progress.create(**entry)

    # Test retrieving progress entries
    inject_security_header("who@cares.com", permission)
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}/progress")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert len(response_data["items"]) == 3

    # Verify entries are sorted by timestamp in ascending order by default
    timestamps = [entry["timestamp"] for entry in response_data["items"]]
    assert timestamps == sorted(timestamps)

    # Verify entry data
    for entry in response_data["items"]:
        assert entry["job_submission_id"] == inserted_job_submission_id
        assert "timestamp" in entry
        assert "slurm_job_state" in entry
        assert "additional_info" in entry


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submission_progress__sort_descending(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/progress with sort_ascending=false.

    This test proves that progress entries can be retrieved in descending order when
    sort_ascending=false is specified.
    """
    # Create a job script and submission
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())
    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    # Create progress entries with different timestamps
    progress_entries = [
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=30),
            "slurm_job_state": SlurmJobState.PENDING,
            "additional_info": "Job is pending",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=20),
            "slurm_job_state": SlurmJobState.RUNNING,
            "additional_info": "Job is running",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
            "slurm_job_state": SlurmJobState.COMPLETED,
            "additional_info": "Job completed successfully",
        },
    ]

    for entry in progress_entries:
        await synth_services.crud.job_progress.create(**entry)

    # Test retrieving progress entries in descending order
    inject_security_header("who@cares.com", permission)
    response = await client.get(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}/progress?sort_ascending=false"
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert len(response_data["items"]) == 3

    # Verify entries are sorted by timestamp in descending order
    timestamps = [entry["timestamp"] for entry in response_data["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submission_progress__sort_by_state(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/progress with sort_field=slurm_job_state.

    This test proves that progress entries can be sorted by slurm_job_state when
    sort_field=slurm_job_state is specified.
    """
    # Create a job script and submission
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())
    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    # Create progress entries with different states
    progress_entries = [
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=30),
            "slurm_job_state": SlurmJobState.PENDING,
            "additional_info": "Job is pending",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=20),
            "slurm_job_state": SlurmJobState.RUNNING,
            "additional_info": "Job is running",
        },
        {
            "job_submission_id": inserted_job_submission_id,
            "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
            "slurm_job_state": SlurmJobState.COMPLETED,
            "additional_info": "Job completed successfully",
        },
    ]

    for entry in progress_entries:
        await synth_services.crud.job_progress.create(**entry)

    # Test retrieving progress entries sorted by state
    inject_security_header("who@cares.com", permission)
    response = await client.get(
        f"/jobbergate/job-submissions/{inserted_job_submission_id}/progress?sort_field=slurm_job_state"
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert len(response_data["items"]) == 3

    # Verify entries are sorted by slurm_job_state
    states = [entry["slurm_job_state"] for entry in response_data["items"]]
    assert states == sorted(states)


@pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ))
async def test_job_submission_progress__no_entries(
    permission,
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
):
    """
    Test GET /job-submissions/{job_submission_id}/progress returns empty list when no entries exist.

    This test proves that the endpoint returns an empty list of progress entries when
    no entries exist for the given job submission.
    """
    # Create a job script and submission
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())
    inserted_job_script_id = base_job_script.id

    inserted_submission = await synth_services.crud.job_submission.create(
        job_script_id=inserted_job_script_id,
        **fill_job_submission_data(
            client_id="dummy-client",
            status=JobSubmissionStatus.SUBMITTED,
            slurm_job_id=111,
            slurm_job_state=SlurmJobState.PENDING,
            slurm_job_info="Fake slurm job info",
        ),
    )
    inserted_job_submission_id = inserted_submission.id

    # Test retrieving progress entries when none exist
    inject_security_header("who@cares.com", permission)
    response = await client.get(f"/jobbergate/job-submissions/{inserted_job_submission_id}/progress")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert len(response_data["items"]) == 0
