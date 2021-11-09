"""
Tests for the /applications/ endpoint.
"""
from io import StringIO
from unittest import mock

import pytest
from fastapi import status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.routers import s3man
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.storage import database
from jobbergateapi2.tests.apps.conftest import insert_objects


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_create_application(s3man_client_mock, application_data, client, inject_security_header):
    """
    Test POST /applications/ correctly creates an application.

    This test proves that an application is successfully created via a POST request to the /applications/
    endpoint. We show this by asserting that the application is created in the database after the post
    request is made, the correct status code (201) is returned and the correct boto3 method was called.
    """
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    inject_security_header("owner1", "jobbergate:applications:create")
    response = await client.post("/applications/", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_201_CREATED
    s3man.s3_client.put_object.assert_called_once()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    query = applications_table.select(applications_table.c.id == 1)
    application = Application.parse_obj(await database.fetch_one(query))

    assert application is not None
    assert application.application_name == application_data["application_name"]
    assert application.application_owner_id == "owner1"
    assert application.application_config == application_data["application_config"]
    assert application.application_file == application_data["application_file"]
    assert application.application_description == ""


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_create_application_bad_permission(
    s3man_client_mock, application_data, client, inject_security_header,
):
    """
    Test that it is not possible to create application without proper permission.

    This test proves that is not possible to create an application without the proper permission.
    We show this by trying to create an application without an permission that allow "create" then assert
    that the application still does not exists in the database, the correct status code (403) is returned
    and that the boto3 method is never called.
    """
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    inject_security_header("owner1", "INVALID_PERMISSION")
    response = await client.post("/applications/", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    s3man.s3_client.put_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_create_without_application_name(
    s3man_client_mock, application_data, client, inject_security_header,
):
    """
    Test that is not possible to create an application without the required parameters.

    This test proves that is not possible to create an application without the name. We show this by
    trying to create an application without the application_name in the request then assert that the
    application still does not exists in the database, the correct status code (422) is returned and that the
    boto3 method is never called.
    """
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    inject_security_header("owner1", "jobbergate:applications:create")
    application_data["application_name"] = None
    response = await client.post("/applications/", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    s3man.s3_client.put_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_create_without_file(
    s3man_client_mock, application_data, client, inject_security_header,
):
    """
    Test that is not possible to create an application without a file.

    This test proves that is not possible to create an application without a file. We show this by
    trying to create an application without a file in the request then assert that the application still
    does not exists in the database, the correct status code (422) is returned and that the boto3 method
    is never called.
    """
    inject_security_header("owner1", "jobbergate:applications:create")
    application_data["application_name"] = None
    response = await client.post("/applications/", data=application_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    s3man.s3_client.put_object.assert_not_called()

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_delete_application(
    s3man_client_mock, client, application_data, inject_security_header,
):
    """
    Test DELETE /applications/<id> correctly deletes an application.

    This test proves that an application is successfully deleted via a DELETE request to the
    /applciations/<id> endpoint. We show this by asserting that the application no longer exists in the
    database after the delete request is made, the correct status code is returned and the correct boto3
    method was called.
    """
    application = [Application(application_owner_id="owner1", **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "jobbergate:applications:delete")
    response = await client.delete("/applications/1")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0
    s3man.s3_client.delete_object.assert_called_once()


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_delete_application_bad_permission(
    s3man_client_mock, client, application_data, inject_security_header,
):
    """
    Test that it is not possible to delete application without proper permission.

    This test proves that an application is not deleted via a DELETE request to the /applciations/<id>
    endpoint. We show this by asserting that the application still exists in the database after the delete
    request is made, the correct status code is returned and the boto3 method is never called.
    """
    application = [Application(application_owner_id="owner1", **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "INVALID_PERMISSION")
    response = await client.delete("/applications/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1
    s3man.s3_client.delete_object.assert_not_called()


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_delete_application_not_found(
    s3man_client_mock, client, application_data, inject_security_header,
):
    """
    Test DELETE /applications/<id> the correct response code when the application doesn't exist.

    This test proves that DELETE /applications/<id> returns the correct response code (404)
    when the application id does not exist in the database. We show this by asserting that a 404 response
    code is returned for a request made with an application id that doesn't exist.
    """
    application = [Application(id=1, application_owner_id="owner1", **application_data)]
    await insert_objects(application, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "jobbergate:applications:delete")
    response = await client.delete("/applications/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1
    s3man.s3_client.delete_object.assert_not_called()


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_delete_application_without_id(
    s3man_client_mock, client, application_data, inject_security_header,
):
    """
    Test DELETE /applications/ without <id> returns the correct response.

    This test proves that DELETE /applications returns the correct response code (405)
    when an application id is not specified. We show this by asserting that a 405 response
    code is returned for a request made without an application id.
    """
    inject_security_header("owner1", "jobbergate:applications:delete")
    response = await client.delete("/applications/")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    s3man.s3_client.delete_object.assert_not_called()


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_by_id(
    client, application_data, inject_security_header,
):
    """
    Test GET /applications/<id>.

    This test proves that GET /applications/<id> returns the correct application, owned by
    the user making the request. We show this by asserting that the application data
    returned in the response is equal to the application data that exists in the database
    for the given application id.
    """
    application = [Application(id=1, application_owner_id="owner1", **application_data)]
    await insert_objects(application, applications_table)

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["application_name"] == application_data["application_name"]
    assert data["application_config"] == application_data["application_config"]
    assert data["application_file"] == application_data["application_file"]


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_by_id_invalid(client, inject_security_header):
    """
    Test the correct response code is returned when an application does not exist.

    This test proves that GET /application/<id> returns the correct response code when the
    requested application does not exist. We show this by asserting that the status code
    returned is what we would expect given the application requested doesn't exist (404).
    """
    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/10")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_by_id_bad_permission(client, application_data, inject_security_header):
    """
    Test that it is not possible to get application without proper permission.

    This test proves that GET /application/<id> returns the correct response code when the
    user don't have the proper permission. We show this by asserting that the status code
    returned is what we would expect (403).
    """
    application = [Application(id=1, application_owner_id="owner1", **application_data)]
    await insert_objects(application, applications_table)

    inject_security_header("owner1", "INVALID_PERMISSION")
    response = await client.get("/applications/1")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_all_from_user(client, application_data, inject_security_header):
    """
    Test GET /applications returns only applications owned by the user making the request.

    This test proves that GET /applications returns the correct applications for the user making
    the request. We show this by asserting that the applications returned in the response are
    only applications owned by the user making the request.
    """
    applications = [
        Application(id=1, application_owner_id="owner1", **application_data),
        Application(id=2, application_owner_id="owner1", **application_data),
        Application(id=3, application_owner_id="owner999", **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_all_from_user_bad_permission(client, application_data, inject_security_header):
    """
    Test that it is not possible to list applications without proper permission.

    This test proves that the GET /applications returns 403 as status code in the response.
    We show this by making a request with an user without creating the permission, and then asserting the
    status code in the response.
    """
    applications = [
        Application(id=1, application_owner_id="owner1", **application_data),
        Application(id=2, application_owner_id="owner1", **application_data),
        Application(id=3, application_owner_id="owner999", **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1", "INVALID_PERMISSION")
    response = await client.get("/applications/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_application_all_from_user_empty(client, application_data, inject_security_header):
    """
    Test applications list doesn't include applications owned by other users.

    This test proves that the user making the request cannot see applications owned by other users.
    We show this by creating applications that are owned by another user id and assert that
    the user making the request to list applications doesn't see any of the other user's
    applications in the response, len(resp.json()) == 0.
    """
    applications = [
        Application(id=1, application_owner_id=999, **application_data),
        Application(id=2, application_owner_id=999, **application_data),
        Application(id=3, application_owner_id=999, **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 0


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_all_applications(client, application_data, inject_security_header):
    """
    Test that listing applications, when all=True, contains applications owned by other users.

    This test proves that the user making the request can see applications owned by other users.
    We show this by creating three applications, two that are owned by the user making the request, and one
    owned by another user. Assert that the response to GET /applications/?all=True includes all three
    applications.
    """
    applications = [
        Application(id=1, application_owner_id="owner1", **application_data),
        Application(id=2, application_owner_id="owner1", **application_data),
        Application(id=3, application_owner_id="owner999", **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/?all=True")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2
    assert data[2]["id"] == 3


@pytest.mark.asyncio
@database.transaction(force_rollback=True)
async def test_get_all_applications_pagination(client, application_data, inject_security_header):
    """
    Test that listing applications works with pagination.

    This test proves that the user making the request can see applications paginated.
    We show this by creating three applications and assert that the response is correctly paginated.
    """
    applications = [
        Application(id=1, application_owner_id="owner1", **application_data),
        Application(id=2, application_owner_id="owner1", **application_data),
        Application(id=3, application_owner_id="owner1", **application_data),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 3

    inject_security_header("owner1", "jobbergate:applications:read")
    response = await client.get("/applications/?limit=1&skip=0")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert [d["id"] for d in data] == [1]

    response = await client.get("/applications/?limit=2&skip=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert [d["id"] for d in data] == [2, 3]


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_update_application(s3man_client_mock, client, application_data, inject_security_header):
    """
    Test that an application is updated via PUT.

    This test proves that an application's values are correctly updated following a PUT request to the
    /application/<id> endpoint. We show this by asserting that the values provided to update the
    application are returned in the response made to the PUT /applciation/<id> endpoint.
    """
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    applications = [
        Application(
            id=1, application_owner_id="owner1", application_description="old description", **application_data
        ),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "jobbergate:applications:update")
    application_data["application_name"] = "new_name"
    application_data["application_description"] = "new_description"
    response = await client.put("/applications/1", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["application_name"] == application_data["application_name"]
    assert data["application_description"] == application_data["application_description"]

    s3man.s3_client.put_object.assert_called_once()

    query = applications_table.select(applications_table.c.id == 1)
    application = Application.parse_obj(await database.fetch_one(query))

    assert application is not None
    assert application.application_name == application_data["application_name"]
    assert application.application_owner_id == "owner1"
    assert application.application_config == application_data["application_config"]
    assert application.application_file == application_data["application_file"]
    assert application.application_description == application_data["application_description"]


@pytest.mark.asyncio
@mock.patch.object(s3man, "s3_client")
@database.transaction(force_rollback=True)
async def test_update_application_bad_permission(
    s3man_client_mock, client, application_data, inject_security_header,
):
    """
    Test that it is not possible to update applications without proper permission.

    This test proves that an application's values are not updated following a PUT request to the
    /application/<id> endpoint by a user without permission. We show this by asserting that the s3_client is
    not called, the status code 403 is returned and that the application_data is still the same as before.
    """
    file_mock = mock.MagicMock(wraps=StringIO("test"))

    applications = [
        Application(
            id=1,
            application_owner_id="owner1",
            application_description="old description",
            **application_data,
        ),
    ]
    await insert_objects(applications, applications_table)
    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 1

    inject_security_header("owner1", "INVALID_PERMISSION")
    application_data["application_name"] = "new_name"
    application_data["application_description"] = "new_description"
    response = await client.put("/applications/1", data=application_data, files={"upload_file": file_mock})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    s3man.s3_client.put_object.assert_not_called()

    query = applications_table.select(applications_table.c.id == 1)
    application = Application.parse_obj(await database.fetch_one(query))

    assert application is not None
    assert application.application_name != application_data["application_name"]
    assert application.application_owner_id == "owner1"
    assert application.application_description == "old description"
