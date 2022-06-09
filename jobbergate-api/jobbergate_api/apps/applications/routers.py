"""
Router for the Application resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from sqlalchemy import not_

from jobbergate_api.apps.applications.models import applications_table, searchable_fields, sortable_fields
from jobbergate_api.apps.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.config import settings
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.s3_manager import s3man_applications as s3man
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import INTEGRITY_CHECK_EXCEPTIONS, database, search_clause, sort_clause

router = APIRouter()


@router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationResponse,
    description="Endpoint for application creation",
)
async def applications_create(
    application: ApplicationCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """
    Create new applications using an authenticated user token.
    """
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    create_dict = dict(
        **application.dict(exclude_unset=True),
        application_owner_email=identity_claims.user_email,
    )

    try:
        insert_query = applications_table.insert().returning(applications_table)
        application_data = await database.fetch_one(query=insert_query, values=create_dict)

    except INTEGRITY_CHECK_EXCEPTIONS as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return application_data


@router.post(
    "/applications/{application_id}/upload",
    status_code=status.HTTP_201_CREATED,
    description=(
        "Endpoint for uploading application files. "
        "The file should be a gzipped tar-file (e.g. `jobbergate.tar.gz`)."
    ),
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def applications_upload(
    application_id: int = Query(..., description="id of the application for which to upload a file"),
    upload_file: UploadFile = File(..., description="The gzipped application tar-file to be uploaded"),
    content_length: int = Header(...),
):
    """
    Upload application tarball using an authenticated user token.
    """
    if content_length > settings.MAX_UPLOAD_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded files cannot exceed {settings.MAX_UPLOAD_FILE_SIZE} bytes.",
        )
    s3man[application_id] = upload_file

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=True))
    )
    await database.execute(update_query)


@router.delete(
    "/applications/{application_id}/upload",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint for deleting application tarballs",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def applications_delete_upload(
    application_id: int = Query(..., description="id of the application for which to delete the file"),
):
    """
    Delete application tarball using an authenticated user token.
    """
    select_query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(select_query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
        )
    application = ApplicationResponse.parse_obj(raw_application)

    if not application.application_uploaded:
        return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)

    del s3man[application_id]

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=False))
    )
    await database.execute(update_query)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
        )
    delete_query = applications_table.delete().where(where_stmt)
    await database.execute(delete_query)
    try:
        del s3man[application_id]
    except KeyError:
        # We should ignore KeyErrors from the S3 manager, because the data may have already been removed
        # outside of the API
        pass

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application by identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def application_delete_by_identifier(
    identifier: str = Query(..., description="identifier of the application to delete"),
):
    """
    Delete application from the database and S3 given it's identifier.
    """
    where_stmt = applications_table.c.application_identifier == identifier
    get_query = applications_table.select().where(where_stmt)
    raw_application = await database.fetch_one(get_query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {identifier=} not found.",
        )
    id_ = raw_application["id"]
    delete_query = applications_table.delete().where(where_stmt)
    await database.execute(delete_query)
    try:
        del s3man[id_]
    except KeyError:
        # We should ignore KeyErrors from the S3 manager, because the data may have already been removed
        # outside of the API
        pass

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/applications",
    description="Endpoint to list applications",
    responses=ok_response(ApplicationResponse),
)
async def applications_list(
    user: bool = Query(False),
    all: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_ascending: bool = Query(True),
    pagination: Pagination = Depends(),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW)),
):
    """
    List all applications.
    """
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    query = applications_table.select()
    if user:
        query = query.where(applications_table.c.application_owner_email == identity_claims.user_email)
    if not all:
        query = query.where(not_(applications_table.c.application_identifier.is_(None)))
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))

    return await package_response(ApplicationResponse, query, pagination)


@router.get(
    "/applications/{application_id}",
    description="Endpoint to return an application given the id",
    response_model=ApplicationResponse,
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW))],
)
async def applications_get_by_id(application_id: int = Query(...)):
    """
    Return the application given it's id.
    """
    query = applications_table.select().where(applications_table.c.id == application_id)
    application_data = await database.fetch_one(query)
    if not application_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
        )
    return application_data


@router.put(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update an application given the id",
    response_model=ApplicationResponse,
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def application_update(
    application_id: int,
    application: ApplicationUpdateRequest,
):
    """
    Update an application given it's id.
    """
    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(application.dict(exclude_unset=True))
        .returning(applications_table)
    )
    async with database.transaction():
        try:
            application_data = await database.fetch_one(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return application_data


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
