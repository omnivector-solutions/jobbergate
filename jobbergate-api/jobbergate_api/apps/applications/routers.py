"""
Router for the Application resource.
"""

from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import not_

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from jobbergate_api.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergate_api.pagination import Pagination, Response, package_response
from jobbergate_api.s3_manager import S3Manager
from jobbergate_api.security import ArmadaClaims, guard
from jobbergate_api.storage import database, handle_fk_error

router = APIRouter()
s3man = S3Manager()


@router.post(
    "/applications/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationResponse,
    description="Endpoint for application creation",
)
async def applications_create(
    application: ApplicationCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:applications:create")),
):
    """
    Create new applications using an authenticated user token.
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    application.application_owner_email = armada_claims.user_email

    async with database.transaction():
        try:
            insert_query = applications_table.insert()
            values = application.dict()
            inserted_id = await database.execute(query=insert_query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        # Now fetch the newly inserted row. This is necessary to reflect defaults and db modified columns
        query = applications_table.select().where(applications_table.c.id == inserted_id)
        raw_application = await database.fetch_one(query)
        response_application = ApplicationResponse.parse_obj(raw_application)

    return response_application


@router.post(
    "/applications/{application_id}/upload",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for uploading application tarballs. Should be gzipped as `jobbergate.tar.gz`.",
    dependencies=[Depends(guard.lockdown("jobbergate:applications:upload"))],
)
async def applications_upload(
    application_id: int = Query(..., description="id of the application for which to upload a file"),
    upload_file: UploadFile = File(..., description="The application tarball to be uploaded"),
):
    """
    Upload application tarball using an authenticated user token.
    """
    s3man.put(upload_file, app_id=str(application_id))


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application",
    dependencies=[Depends(guard.lockdown("jobbergate:applications:delete"))],
)
async def application_delete(
    application_id: int = Query(..., description="id of the application to delete"),
):
    """
    Delete application from the database and S3 given it's id.
    """
    where_stmt = applications_table.c.id == application_id
    get_query = applications_table.select().where(where_stmt)
    raw_application = await database.fetch_one(get_query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id=} not found.",
        )
    delete_query = applications_table.delete().where(where_stmt)
    with handle_fk_error():
        await database.execute(delete_query)
    try:
        s3man.delete(app_id=str(application_id))
    except KeyError:
        # We should ignore KeyErrors from the S3 manager, because the data may have already been removed
        # outside of the API
        pass


@router.get(
    "/applications/",
    description="Endpoint to list applications",
    response_model=Response[ApplicationResponse],
)
async def applications_list(
    user: bool = Query(False),
    all: bool = Query(False),
    pagination: Pagination = Depends(),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:applications:read")),
):
    """
    List all applications
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    query = applications_table.select()
    if user:
        query = query.where(applications_table.c.application_owner_email == armada_claims.user_email)
    if not all:
        query = query.where(not_(applications_table.c.application_identifier.is_(None)))
    return await package_response(ApplicationResponse, query, pagination)


@router.get(
    "/applications/{application_id}",
    description="Endpoint to return an application given the id",
    response_model=ApplicationResponse,
    dependencies=[Depends(guard.lockdown("jobbergate:applications:read"))],
)
async def applications_get_by_id(application_id: int = Query(...)):
    """
    Return the application given it's id.
    """
    query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id=} not found.",
        )
    application = ApplicationResponse.parse_obj(raw_application)

    return application


@router.put(
    "/applications/{application_id}",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to update an application given the id",
    response_model=ApplicationResponse,
    dependencies=[Depends(guard.lockdown("jobbergate:applications:update"))],
)
async def application_update(
    application_id: int, application: ApplicationUpdateRequest,
):
    """
    Update an application given it's id.
    """
    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(application.dict(exclude_unset=True))
    )
    async with database.transaction():
        try:
            await database.execute(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        select_query = applications_table.select().where(applications_table.c.id == application_id)
        raw_application = await database.fetch_one(select_query)
        response_application = ApplicationResponse.parse_obj(raw_application)

    return response_application


def include_router(app):
    app.include_router(router)
