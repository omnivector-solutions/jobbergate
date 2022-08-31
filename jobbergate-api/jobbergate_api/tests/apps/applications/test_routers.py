"""
Tests for the /applications/ endpoint.
"""
import json
from unittest import mock

import asyncpg
import pytest
from fastapi import status

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationPartialResponse
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import database, fetch_instance


@pytest.mark.asyncio
async def test_create_application(
    fill_application_data,
    client,
    inject_security_header,
    time_frame,
):
    """
    Test POST /applications/ correctly creates an application.

    This test proves that an application is successfully created via a POST request to the /applications/
    endpoint. We show this by asserting that the application is created in the database after the post
    request is made and the correct status code (201) is returned.
    """
    id_rows = await database.fetch_all("SELECT id FROM applications")
    assert len(id_rows) == 0

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    with time_frame() as window:
        response = await client.post(
            "/jobbergate/applications/",
            json=fill_application_data(
                application_name="test-name",
                application_identifier="test-identifier",
            ),
        )

    assert response.status_code == status.HTTP_201_CREATED

    id_rows = await database.fetch_all("SELECT id FROM applications")
    assert len(id_rows) == 1

    application = ApplicationPartialResponse(**response.json())

    assert application.id == id_rows[0][0]
    assert application.application_name == "test-name"
    assert application.application_identifier == "test-identifier"
    assert application.application_owner_email == "owner1@org.com"
    assert application.application_description is None
    assert application.created_at in window
    assert application.updated_at in window


@pytest.mark.asyncio
async def test_create_application_bad_permission(
    application_data,
    client,
    inject_security_header,
):
    """
    Test that it is not possible to create application without proper permission.

    This test proves that is not possible to create an application without the proper permission.
    We show this by trying to create an application without an permission that allow "create" then assert
    that the application still does not exists in the database and that the correct status code (403) is
    returned.
    """
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.post("/jobbergate/applications/", json=application_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
async def test_create_without_application_name(
    application_data,
    client,
    inject_security_header,
):
    """
    Test that is not possible to create an application without the required body fields.

    This test proves that is not possible to create an application without the name. We show this by
    trying to create an application without the application_name in the request then assert that the
    application still does not exists in the database and the correct status code (422) is returned.
    """
    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.post(
        "/jobbergate/applications/",
        json={k: v for (k, v) in application_data.items() if k != "application_name"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.delete_from_s3")
async def test_delete_application_no_file_uploaded(
    mocked_application_deleter, client, application_data, inject_security_header
):
    """
    Test DELETE /applications/<id> correctly deletes an application.

    This test proves that an application is successfully deleted via a DELETE request to the
    /applications/<id> endpoint. We show this by asserting that the application no longer exists in the
    database after the delete request is made and the correct status code is returned.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=application_data,
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.delete(f"/jobbergate/applications/{inserted_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0

    mocked_application_deleter.assert_called_once_with(inserted_id)


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.delete_from_s3")
async def test_delete_application_with_uploaded_file(
    mocked_application_deleter, client, application_data, inject_security_header
):
    """
    Test DELETE /applications/<id> correctly deletes an application and it's file.

    This test proves that an application is successfully deleted via a DELETE request to the
    /applications/<id> endpoint. We show this by asserting that the application no longer exists in the
    database after the delete request is made, the correct status code is returned and the correct boto3
    method was called.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=application_data,
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.delete(f"/jobbergate/applications/{inserted_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0

    mocked_application_deleter.assert_called_once_with(inserted_id)


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.delete_from_s3")
async def test_delete_application_by_identifier(
    mocked_application_deleter, client, fill_application_data, inject_security_header
):
    """
    Test DELETE /applications?identifier=<identifier> correctly deletes an application and it's file.

    This test proves that an application is successfully deleted via a DELETE request to the
    /applications?identifier=<identifier> endpoint. We show this by asserting that the application no longer
    exists in the database after the delete request is made, the correct status code is returned and the
    correct boto3 method was called.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(
            application_owner_email="owner1@org.com",
            application_identifier="test-identifier",
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.delete("/jobbergate/applications?identifier=test-identifier")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0

    mocked_application_deleter.assert_called_once_with(inserted_id)


@pytest.mark.asyncio
async def test_delete_application_bad_permission(
    client,
    application_data,
    inject_security_header,
):
    """
    Test that it is not possible to delete application without proper permission.

    This test proves that an application is not deleted via a DELETE request to the /applications/<id>
    endpoint. We show this by asserting that the application still exists in the database after the delete
    request is made and the correct status code is returned.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=application_data,
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.delete(f"/jobbergate/applications/{inserted_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1


@pytest.mark.asyncio
async def test_delete_application_not_found(client, inject_security_header):
    """
    Test DELETE /applications/<id> the correct response code when the application doesn't exist.

    This test proves that DELETE /applications/<id> returns the correct response code (404)
    when the application id does not exist in the database. We show this by asserting that a 404 response
    code is returned for a request made with an application id that doesn't exist.
    """
    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.delete("/jobbergate/applications/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_application__fk_error(
    client,
    application_data,
    inject_security_header,
):
    """
    Test DELETE /applications/<id> correctly returns a 409 when a foreign-key error occurs.

    Test that a helpful message when a delete is blocked by a foreign-key constraint.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=application_data,
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    with mock.patch(
        "jobbergate_api.storage.database.execute",
        side_effect=asyncpg.exceptions.ForeignKeyViolationError(
            f"""
            update or delete on table "applications" violates foreign key constraint
            "job_scripts_application_id_fkey" on table "job_scripts"
            DETAIL:  Key (id)=({inserted_id}) is still referenced from table "job_scripts".
            """
        ),
    ):
        response = await client.delete(f"/jobbergate/applications/{inserted_id}")
    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = json.loads(response.text)["detail"]
    assert error_data["message"] == "Delete failed due to foreign-key constraint"
    assert error_data["table"] == "job_scripts"
    assert error_data["pk_id"] == f"{inserted_id}"


@pytest.mark.asyncio
async def test_get_application_by_id__files_not_uploaded(
    client,
    fill_application_data,
    inject_security_header,
):
    """
    Test GET /applications/<id> when the application files were not uploaded.

    This test proves that GET /applications/<id> returns the correct application, owned by
    the user making the request. We show this by asserting that the application data
    returned in the response is equal to the application data that exists in the database
    for the given application id.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_identifier="app1"),
    )
    await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_identifier="app2"),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 2

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get(f"/jobbergate/applications/{inserted_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_id
    assert data["application_identifier"] == "app1"
    assert data["application_uploaded"] is False
    assert data["application_source_file"] is None
    assert data["application_templates"] is None


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.get_from_s3")
async def test_get_application_by_id__files_uploaded(
    mocked_get_application_files_from_s3,
    client,
    fill_application_data,
    inject_security_header,
    dummy_application_config,
    dummy_application_source_file,
    dummy_template,
):
    """
    Test GET /applications/<id> when the application files were uploaded.

    This test proves that GET /applications/<id> returns the correct application, owned by
    the user making the request. We show this by asserting that the application data
    returned in the response is equal to the application data that exists in the database
    for the given application id, and the application files are recovered from S3.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(
            application_identifier="app1",
            application_uploaded=True,
        ),
    )
    await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_identifier="app2"),
    )

    mocked_get_application_files_from_s3.return_value = ApplicationFiles(
        templates={"test_job_script.sh": dummy_template},
        source_file=dummy_application_source_file,
        config_file=dummy_application_config,
    )

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 2

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get(f"/jobbergate/applications/{inserted_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == inserted_id
    assert data["application_identifier"] == "app1"
    assert data["application_uploaded"] is True
    assert data["application_config"] == dummy_application_config
    assert data["application_source_file"] == dummy_application_source_file
    assert data["application_templates"] == {"test_job_script.sh": dummy_template}


@pytest.mark.asyncio
async def test_get_application_by_id_invalid(client, inject_security_header):
    """
    Test the correct response code is returned when an application does not exist.

    This test proves that GET /application/<id> returns the correct response code when the
    requested application does not exist. We show this by asserting that the status code
    returned is what we would expect given the application requested doesn't exist (404).
    """
    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get("/jobbergate/applications/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_application_by_id_bad_permission(
    client,
    application_data,
    inject_security_header,
):
    """
    Test that it is not possible to get application without proper permission.

    This test proves that GET /application/<id> returns the correct response code when the
    user don't have the proper permission. We show this by asserting that the status code
    returned is what we would expect (403).
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=application_data,
    )

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get(f"/jobbergate/applications/{inserted_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_applications__no_params(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test GET /applications returns only applications owned by the user making the request.

    This test proves that GET /applications returns the correct applications for the user making
    the request. We show this by asserting that the applications returned in the response are
    only applications owned by the user making the request.
    """
    await database.execute_many(
        applications_table.insert(),
        values=fill_all_application_data(
            dict(application_identifier="app1"),
            dict(application_identifier="app2"),
            dict(application_identifier="app3"),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get("/jobbergate/applications/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert sorted([d["application_identifier"] for d in results]) == [
        "app1",
        "app2",
        "app3",
    ]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_application___bad_permission(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test that it is not possible to list applications without proper permission.

    This test proves that the GET /applications returns 403 as status code in the response.
    We show this by making a request with an user without creating the permission, and then asserting the
    status code in the response.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(application_identifier="app1"),
            dict(application_identifier="app2"),
            dict(application_identifier="app3"),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.get("/jobbergate/applications/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_applications__with_user_param(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test applications list doesn't include applications owned by other users with `user` param.

    This test proves that the user making the request cannot see applications owned by other users.
    We show this by creating applications that are owned by another user id and assert that
    the user making the request to list applications doesn't see any of the other user's
    applications in the response
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(
                application_identifier="app1",
                application_owner_email="owner1@org.com",
            ),
            dict(
                application_identifier="app2",
                application_owner_email="owner1@org.com",
            ),
            dict(
                application_identifier="app3",
                application_owner_email="owner999@org.com",
            ),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get("/jobbergate/applications")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert sorted(d["application_identifier"] for d in results) == ["app1", "app2", "app3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )

    response = await client.get("/jobbergate/applications?user=true")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert sorted(d["application_identifier"] for d in results) == ["app1", "app2"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=2,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_applications__with_all_param(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test that listing applications, when all=True, contains applications without identifiers.

    This test proves that the user making the request can see applications owned by other users.
    We show this by creating three applications, two that are owned by the user making the request, and one
    owned by another user. Assert that the response to GET /applications/?all=True includes all three
    applications.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(application_identifier="app1", application_owner_email="owner1@org.com"),
            dict(application_owner_email="owner1@org.com"),
            dict(application_identifier="app3", application_owner_email="owner999@org.com"),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)

    response = await client.get("/jobbergate/applications")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["app1", "app3"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=2,
        start=None,
        limit=None,
    )

    response = await client.get("/jobbergate/applications/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    pagination = data.get("pagination")
    assert pagination == dict(
        total=3,
        start=None,
        limit=None,
    )


@pytest.mark.asyncio
async def test_get_applications__with_search_param(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test that listing applications, when search=<search terms>, returns matches.

    This test proves that the user making the request will be shown applications that match the search string.
    We show this by creating applications and using various search queries to match against them.

    Assert that the response to GET /applications?search=<search terms> includes correct matches.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(
                application_name="test name one",
                application_identifier="app1",
                application_owner_email="one@org.com",
            ),
            dict(
                application_name="test name two",
                application_identifier="app2",
                application_owner_email="two@org.com",
            ),
            dict(
                application_name="test name twenty-two",
                application_identifier="app22",
                application_owner_email="twenty-two@org.com",
                application_description="a long description of this application",
            ),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("admin@org.com", Permissions.APPLICATIONS_VIEW)

    response = await client.get("/jobbergate/applications?all=true&search=one")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["app1"]

    response = await client.get("/jobbergate/applications?all=true&search=two")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert sorted([d["application_identifier"] for d in results]) == ["app2", "app22"]

    response = await client.get("/jobbergate/applications?all=true&search=long")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["app22"]

    response = await client.get("/jobbergate/applications?all=true&search=name+test")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert sorted([d["application_identifier"] for d in results]) == ["app1", "app2", "app22"]


@pytest.mark.asyncio
async def test_get_applications__with_sort_params(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test that listing applications with sort params returns correctly ordered matches.

    This test proves that the user making the request will be shown applications sorted in the correct order
    according to the ``sort_field`` and ``sort_ascending`` parameters.
    We show this by creating applications and using various sort parameters to order them.

    Assert that the response to GET /applications?sort_field=<field>&sort_ascending=<bool> includes correctly
    sorted applications.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(application_name="A", application_identifier="Z"),
            dict(application_name="B", application_identifier="Y"),
            dict(application_name="C", application_identifier="X"),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("admin@org.com", Permissions.APPLICATIONS_VIEW)

    response = await client.get("/jobbergate/applications?all=true&sort_field=application_name")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["Z", "Y", "X"]

    response = await client.get(
        "/jobbergate/applications?all=true&sort_field=application_name&sort_ascending=false"
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/applications?all=true&sort_field=application_identifier")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    results = data.get("results")
    assert [d["application_identifier"] for d in results] == ["X", "Y", "Z"]

    response = await client.get("/jobbergate/applications?all=true&sort_field=application_config")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid sorting column requested" in response.text


@pytest.mark.asyncio
async def test_get_applications__with_pagination(
    client,
    fill_all_application_data,
    inject_security_header,
):
    """
    Test that listing applications works with pagination.

    This test proves that the user making the request can see applications paginated.
    We show this by creating three applications and assert that the response is correctly paginated.
    """
    await database.execute_many(
        query=applications_table.insert(),
        values=fill_all_application_data(
            dict(application_identifier="app1", application_owner_email="owner1@org.com"),
            dict(application_identifier="app2", application_owner_email="owner1@org.com"),
            dict(application_identifier="app3", application_owner_email="owner1@org.com"),
            dict(application_identifier="app4", application_owner_email="owner1@org.com"),
            dict(application_identifier="app5", application_owner_email="owner1@org.com"),
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 5

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_VIEW)
    response = await client.get(
        "/jobbergate/applications/?start=0&limit=1&all=true&sort_field=application_identifier"
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["application_identifier"] for d in results] == ["app1"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=5,
        start=0,
        limit=1,
    )

    response = await client.get("/jobbergate/applications/?start=1&limit=2&all=true")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["application_identifier"] for d in results] == ["app3", "app4"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=5,
        start=1,
        limit=2,
    )

    response = await client.get("/jobbergate/applications/?start=2&limit=2&all=true")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    results = data.get("results")
    assert results
    assert [d["application_identifier"] for d in results] == ["app5"]

    pagination = data.get("pagination")
    assert pagination == dict(
        total=5,
        start=2,
        limit=2,
    )


@pytest.mark.asyncio
async def test_update_application(
    client,
    fill_application_data,
    inject_security_header,
    time_frame,
):
    """
    Test that an application is updated via PUT.

    This test proves that an application's values are correctly updated following a PUT request to the
    /application/<id> endpoint. We show this by asserting that the values provided to update the
    application are returned in the response made to the PUT /application/<id> endpoint.
    """
    await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(
            application_identifier="old_identifier",
            application_owner_email="owner1@org.com",
            application_description="old description",
        ),
    )
    rows = await database.fetch_all("select id from applications")
    assert len(rows) == 1
    id = rows[0][0]

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    with time_frame() as window:
        response = await client.put(
            f"/jobbergate/applications/{id}",
            json=dict(
                application_name="new_name",
                application_identifier="new_identifier",
                application_description="new_description",
            ),
        )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["application_name"] == "new_name"
    assert data["application_identifier"] == "new_identifier"
    assert data["application_description"] == "new_description"

    query = applications_table.select(applications_table.c.id == id)
    result = await database.fetch_one(query)

    assert result is not None
    assert result["application_name"] == "new_name"
    assert result["application_identifier"] == "new_identifier"
    assert result["application_owner_email"] == "owner1@org.com"
    assert result["application_description"] == "new_description"
    assert result["updated_at"] in window


@pytest.mark.asyncio
async def test_update_application_bad_permission(
    client,
    fill_application_data,
    inject_security_header,
):
    """
    Test that it is not possible to update applications without proper permission.

    This test proves that an application's values are not updated following a PUT request to the
    /application/<id> endpoint by a user without permission. We show this by asserting that the status code
    403 is returned and that the application_data is still the same as before.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(
            application_name="old-name",
            application_identifier="old_identifier",
            application_owner_email="owner1@org.com",
            application_description="old description",
        ),
    )
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1@org.com", "INVALID_PERMISSION")
    response = await client.put(
        f"/jobbergate/applications/{inserted_id}",
        json=dict(
            application_name="new_name",
            application_identifier="new_identifier",
            application_description="new_description",
        ),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    query = applications_table.select(applications_table.c.id == inserted_id)
    result = await database.fetch_one(query)

    assert result is not None
    assert result["application_name"] == "old-name"
    assert result["application_identifier"] == "old_identifier"
    assert result["application_description"] == "old description"


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.write_to_s3")
@mock.patch(
    "jobbergate_api.apps.applications.routers.ApplicationFiles.get_from_upload_files",
    return_value=ApplicationFiles(),
)
async def test_upload_file__works_with_small_file(
    mocked_application_writer,
    mocked_application_get_upload,
    client,
    inject_security_header,
    fill_application_data,
    tweak_settings,
    make_dummy_file,
    dummy_application_config,
    make_files_param,
):
    """
    Test that a file is uploaded.

    This test proves that an application's file is uploaded by making sure that the
    boto3 put_object method is called once and a 201 status code is returned. It also
    checks to make sure that the application row in the database has
    `application_uploaded` set.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_owner_email="owner1@org.com"),
    )
    application = await fetch_instance(inserted_id, applications_table, ApplicationPartialResponse)
    assert not application.application_uploaded

    dummy_file = make_dummy_file("jobbergate.yaml", content=dummy_application_config)
    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    with tweak_settings(MAX_UPLOAD_FILE_SIZE=600):
        with make_files_param(dummy_file) as files_param:
            response = await client.post(
                f"/jobbergate/applications/{inserted_id}/upload",
                files=files_param,
            )

    assert response.status_code == status.HTTP_201_CREATED
    mocked_application_writer.assert_called_once()
    mocked_application_get_upload.assert_called_once()

    application = await fetch_instance(inserted_id, applications_table, ApplicationPartialResponse)
    assert application.application_uploaded


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.write_to_s3")
async def test_upload_file__fails_with_413_on_large_file(
    mocked_application_writer,
    client,
    inject_security_header,
    tweak_settings,
    make_dummy_file,
    make_files_param,
):
    """
    Test that upload fails when the files are too large.
    """
    dummy_file = make_dummy_file("dummy.py", size=600 + 200)
    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    with tweak_settings(MAX_UPLOAD_FILE_SIZE=600):
        with make_files_param(dummy_file) as files_param:
            response = await client.post(
                "/jobbergate/applications/1/upload",
                files=files_param,
            )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    mocked_application_writer.assert_not_called()


@pytest.mark.asyncio
@mock.patch("jobbergate_api.apps.applications.routers.ApplicationFiles.delete_from_s3")
async def test_delete_file(mocked_application_deleter, client, inject_security_header, fill_application_data):
    """
    Test that a file is deleted.

    This test proves that an application's file is deleted by making sure that the boto3 put_object method
    is called once and a 201 status code is returned.
    """
    inserted_id = await database.execute(
        query=applications_table.insert(),
        values=fill_application_data(application_owner_email="owner1@org.com", application_uploaded=True),
    )
    application: ApplicationPartialResponse = await fetch_instance(
        inserted_id, applications_table, ApplicationPartialResponse
    )
    assert application.application_uploaded

    inject_security_header("owner1@org.com", Permissions.APPLICATIONS_EDIT)
    response = await client.delete(f"/jobbergate/applications/{inserted_id}/upload")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    mocked_application_deleter.assert_called_once_with(inserted_id)

    application = await fetch_instance(inserted_id, applications_table, ApplicationPartialResponse)
    assert not application.application_uploaded
