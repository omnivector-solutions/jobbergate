"""
Router for the Application resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from loguru import logger
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
from jobbergate_api.s3_manager import s3man_applications
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    database,
    render_sql,
    search_clause,
    sort_clause,
)

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
    logger.debug(f"Creating {application=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    create_dict = dict(
        **application.dict(exclude_unset=True),
        application_owner_email=identity_claims.email,
    )

    logger.debug("Inserting application")

    try:
        insert_query = applications_table.insert().returning(applications_table)
        logger.trace(f"insert_query = {render_sql(insert_query)}")
        application_data = await database.fetch_one(query=insert_query, values=create_dict)

    except INTEGRITY_CHECK_EXCEPTIONS as e:
        logger.error(f"INTEGRITY_CHECK_EXCEPTIONS: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    logger.debug(f"Applications created: {application_data=}")

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
    logger.debug(f"Preparing to upload tarball for {application_id=}")

    if content_length > settings.MAX_UPLOAD_FILE_SIZE:
        message = f"Uploaded files cannot exceed {settings.MAX_UPLOAD_FILE_SIZE} bytes."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=message,
        )
    s3man_applications[application_id] = upload_file.file

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=True))
    )

    logger.trace(f"update_query = {render_sql(update_query)}")
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
    logger.debug(f"Preparing to delete tarball for {application_id=}")

    select_query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(select_query)

    if not raw_application:
        message = f"Application {application_id=} not found."
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    application = ApplicationResponse.parse_obj(raw_application)

    if not application.application_uploaded:
        logger.debug(f"Trying to delete an applications that was not uploaded ({application_id=})")
        return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)

    del s3man_applications[application_id]

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=False))
    )

    logger.trace(f"update_query = {render_sql(update_query)}")
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
    logger.debug(f"Preparing to delete {application_id=} from the database and S3")

    where_stmt = applications_table.c.id == application_id
    get_query = applications_table.select().where(where_stmt)
    logger.trace(f"get_query = {render_sql(get_query)}")

    raw_application = await database.fetch_one(get_query)
    if not raw_application:
        message = f"Application {application_id=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    delete_query = applications_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(delete_query)}")

    await database.execute(delete_query)
    try:
        del s3man_applications[application_id]
    except KeyError:
        # We should ignore KeyErrors from the S3 manager, because the data may
        # have already been removed outside of the API
        logger.debug(f"Tried to delete {application_id=}, but it was not found on S3.")

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
    logger.debug(f"Preparing to delete {identifier=} from the database and S3")

    where_stmt = applications_table.c.application_identifier == identifier
    get_query = applications_table.select().where(where_stmt)
    logger.trace(f"get_query = {render_sql(get_query)}")

    raw_application = await database.fetch_one(get_query)
    if not raw_application:
        message = f"Application {identifier=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    id_ = raw_application["id"]
    delete_query = applications_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(delete_query)}")

    await database.execute(delete_query)

    try:
        del s3man_applications[id_]
    except KeyError:
        # We should ignore KeyErrors from the S3 manager, because the data may have already been removed
        # outside of the API
        logger.warning(f"Tried to delete application_id={id_}, but it was not found on S3.")

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
    logger.debug("Preparing to list the Applications")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    query = applications_table.select()
    if user:
        query = query.where(applications_table.c.application_owner_email == identity_claims.email)
    if not all:
        query = query.where(not_(applications_table.c.application_identifier.is_(None)))
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))

    logger.trace(f"query = {render_sql(query)}")
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
    logger.trace(f"Getting {application_id=}")

    query = applications_table.select().where(applications_table.c.id == application_id)
    logger.trace(f"get_query = {render_sql(query)}")

    application_data = await database.fetch_one(query)
    if not application_data:
        message = f"Application {application_id=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.debug(f"Application data: {application_data=}")

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
    logger.debug(f"Preparing to update {application_id=}")

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(application.dict(exclude_unset=True))
        .returning(applications_table)
    )
    logger.trace(f"update_query = {render_sql(update_query)}")

    async with database.transaction():
        try:
            application_data = await database.fetch_one(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    logger.debug(f"Application data: {application_data=}")

    return application_data


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
