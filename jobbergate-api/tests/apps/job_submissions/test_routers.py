"""
Tests for the /job-submissions/ endpoint.
"""

import json

import pytest
from fastapi import status

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.rabbitmq_notification import rabbitmq_connect

# Not using the synth_session fixture in a route that needs the database is unsafe
pytest.mark.usefixtures("synth_session")


async def test_create_job_submission__on_site_submission(
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")
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


async def test_create_job_submission__with_client_id_in_token(
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")
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

    created_id = response_data["id"]

    # Make sure that the data can be retrieved with a GET request
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-cluster-client")
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
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
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
    we assert that a 400 response is returned.k
    """
    base_job_script = await synth_services.crud.job_script.create(**fill_job_script_data())

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


async def test_get_job_submission_by_id(
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_VIEW)
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
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions", params=dict(user_only=True))
    assert unpack_response(response, key="name", sort=True) == ["sub1", "sub3"]


async def test_get_job_submissions__include_archived(
    client,
    fill_all_job_submission_data,
    inject_security_header,
    synth_session,
    unpack_response,
    synth_services,
):
    """
    Test that the is archived field makes no effect when listing job_submissions.

    The archive feature is shared across all tables, but it is not planned to work on job submissions yet,
    ir order to keep feature parity with version 3.x. It may be implemented in the future.
    """
    all_create_data = fill_all_job_submission_data({"is_archived": False}, {"is_archived": True})

    for create_data in all_create_data:
        await synth_services.crud.job_submission.create(**create_data)

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions", params=dict(user_only=False))
    assert unpack_response(response, key="is_archived", sort=True) == [False, True]


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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

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

    inject_security_header("admin@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
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

    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)

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
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_VIEW)
    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=101-103")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text

    response = await client.get("/jobbergate/job-submissions?slurm_job_ids=one-oh-one")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Invalid slurm_job_ids" in response.text


async def test_update_job_submission__basic(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    synth_services,
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT)
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
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
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


async def test_delete_job_submission(
    client,
    fill_job_script_data,
    fill_job_submission_data,
    tester_email,
    inject_security_header,
    synth_services,
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

    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.delete(f"/jobbergate/job-submissions/{inserted_job_submission_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    await synth_services.crud.job_submission.count() == 0


async def test_delete_job_submission_not_found(client, inject_security_header, synth_session):
    """
    Test that it is not possible to delete a job_submission that is not found.

    This test proves that it is not possible to delete a job_submission if it does not exists. We show this
    by asserting that a 404 response status code is returned.
    """
    inject_security_header("owner1@org.com", Permissions.JOB_SUBMISSIONS_EDIT)
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


async def test_job_submissions_agent_pending__success(
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
        await synth_services.crud.job_submission.create(**item)

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
    assert [i["job_script"]["id"] for i in data["items"]] == [inserted_job_script_id] * 2

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
        Permissions.JOB_SUBMISSIONS_VIEW,
    )
    response = await client.get("/jobbergate/job-submissions/agent/pending")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Access token does not contain\\n  1: client_id" in response.text


async def test_job_submissions_agent_submitted__success(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
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
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.post(f"/jobbergate/job-submissions/agent/submitted", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.SUBMITTED
    assert instance.slurm_job_id == payload["slurm_job_id"]


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
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.post(f"/jobbergate/job-submissions/agent/submitted", json=payload)
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
    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT)
    response = await client.put(
        "/jobbergate/job-submissions/agent/1",
        json=dict(status=JobSubmissionStatus.SUBMITTED, slurm_job_id=111),
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
    )

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="stupid-client")
    response = await client.post(f"/jobbergate/job-submissions/agent/submitted", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_job_submissions_agent_rejected__success(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
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

    inject_security_header(
        "who@cares.com",
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-client",
        organization_id="dummy-org",
    )
    response = await client.post(f"/jobbergate/job-submissions/agent/rejected", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.REJECTED
    assert instance.report_message == payload["report_message"]


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
        Permissions.JOB_SUBMISSIONS_EDIT,
        client_id="dummy-client",
        organization_id="dummy-org",
    )
    response = await client.post(f"/jobbergate/job-submissions/agent/rejected", json=payload)
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.post(f"/jobbergate/job-submissions/agent/rejected", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only CREATED Job Submissions can be marked as REJECTED" in response.text


async def test_job_submissions_agent_update__success(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=111,
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    instance = await synth_services.crud.job_submission.get(inserted_job_submission_id)
    assert instance.id == inserted_job_submission_id
    assert instance.status == JobSubmissionStatus.SUBMITTED
    assert instance.slurm_job_state == SlurmJobState.RUNNING
    assert instance.slurm_job_info == "Dummy slurm job info"
    assert instance.slurm_job_id == 111


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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
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


async def test_job_submissions_agent_update__sets_done_status(
    fill_job_script_data,
    fill_job_submission_data,
    client,
    inject_security_header,
    synth_services,
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
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
        Permissions.JOB_SUBMISSIONS_EDIT,
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
    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT)
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="stupid-client")
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT, client_id="dummy-client")
    response = await client.put(
        f"/jobbergate/job-submissions/agent/{inserted_job_submission_id}",
        json=dict(
            slurm_job_state=SlurmJobState.RUNNING,
            slurm_job_info="Dummy slurm job info",
            slurm_job_id=222,
        ),
    )
    assert response.status_code == status.HTTP_409_CONFLICT


async def test_job_submissions_agent_active__success(
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

    inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_VIEW, client_id="dummy-client")
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
        Permissions.JOB_SUBMISSIONS_VIEW,
    )
    response = await client.get("/jobbergate/job-submissions/agent/active")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Access token does not contain\\n  1: client_id" in response.text
