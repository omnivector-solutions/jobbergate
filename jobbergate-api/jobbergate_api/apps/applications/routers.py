"""
Router for the Application resource.
"""
from pathlib import PurePath
from typing import List, Optional, Union

from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from loguru import logger
from sqlalchemy import not_

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table, searchable_fields, sortable_fields
from jobbergate_api.apps.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationPartialResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.permissions import Permissions, check_owner
from jobbergate_api.config import settings
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    database,
    render_sql,
    search_clause,
    sort_clause,
)

router = APIRouter()


async def _fetch_application_by_id(application_id: int) -> ApplicationPartialResponse:
    """
    Fetch an application from the database by its id.
    """
    select_query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(select_query)

    if not raw_application:
        message = f"Application {application_id=} not found."
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    return ApplicationPartialResponse.parse_obj(raw_application)


@router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationPartialResponse,
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
    description="Endpoint for uploading application files.",
)
async def applications_upload(
    application_id: int = Query(..., description="id of the application for which to upload a file"),
    upload_files: List[UploadFile] = File(..., description="The application files to be uploaded"),
    content_length: int = Header(...),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """
    Upload application files using an authenticated user token.
    """
    logger.debug(f"Preparing to receive upload files for {application_id=}")

    if content_length > settings.MAX_UPLOAD_FILE_SIZE:
        message = f"Uploaded files cannot exceed {settings.MAX_UPLOAD_FILE_SIZE} bytes."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=message,
        )

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    application = await _fetch_application_by_id(application_id)
    check_owner(application.application_owner_email, identity_claims.email, application_id, "application")

    ApplicationFiles.get_from_upload_files(upload_files).write_to_s3(application_id)

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=True))
    )

    logger.trace(f"update_query = {render_sql(update_query)}")
    await database.execute(update_query)


@router.patch(
    "/applications/{application_id}/upload/individually",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "File(s) was(were) patched successfully"},
        403: {"description": "User does not own application"},
    },
)
async def update_application_source_file(
    application_id: int = Query(..., description="id of the application for which to upload a file"),
    source_file: Union[UploadFile, None] = File(default=None),
    config_file: Union[UploadFile, None] = File(default=None),
    template_files: Union[List[UploadFile], None] = None,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """Update the application files individually."""
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    application = await _fetch_application_by_id(application_id)
    check_owner(application.application_owner_email, identity_claims.email, application_id, "application")

    # TODO: limit by file size
    ApplicationFiles(
        application_config=config_file.file.read().decode("utf-8") if config_file is not None else None,
        application_source_file=source_file.file.read().decode("utf-8") if source_file is not None else None,
        application_templates={
            PurePath(template_file.filename).name: template_file.file.read().decode("utf-8")
            for template_file in template_files
        }
        if template_files is not None
        else {},
    ).write_to_s3(application_id, remove_previous_files=False)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications/{application_id}/upload",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint for deleting application files",
)
async def applications_delete_upload(
    application_id: int = Query(..., description="id of the application for which to delete the file"),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """
    Delete application files using an authenticated user token.
    """
    logger.debug(f"Preparing to delete files for {application_id=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    application = await _fetch_application_by_id(application_id)
    check_owner(application.application_owner_email, identity_claims.email, application_id, "application")

    if not application.application_uploaded:
        logger.debug(f"Trying to delete an applications that was not uploaded ({application_id=})")
        return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)

    ApplicationFiles.delete_from_s3(application_id)

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
)
async def application_delete(
    application_id: int = Query(..., description="id of the application to delete"),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """
    Delete application from the database and S3 given its id.
    """
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    application = await _fetch_application_by_id(application_id)
    check_owner(application.application_owner_email, identity_claims.email, application_id, "application")

    logger.debug(f"Orphaning job_scripts rendered from application {application_id=}")
    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.application_id == application_id)
        .values(dict(application_id=None))
    )

    logger.trace(f"update_query = {render_sql(update_query)}")
    await database.execute(update_query)

    logger.debug(f"Preparing to delete {application_id=} from the database and S3")

    where_stmt = applications_table.c.id == application_id
    delete_query = applications_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(delete_query)}")

    await database.execute(delete_query)

    ApplicationFiles.delete_from_s3(application_id)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application by identifier",
)
async def application_delete_by_identifier(
    identifier: str = Query(..., description="identifier of the application to delete"),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
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
    application = ApplicationPartialResponse.parse_obj(raw_application)

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    check_owner(application.application_owner_email, identity_claims.email, application.id, "application")

    delete_query = applications_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(delete_query)}")

    await database.execute(delete_query)

    ApplicationFiles.delete_from_s3(application.id)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/applications",
    description="Endpoint to list applications",
    responses=ok_response(ApplicationPartialResponse),
)
async def applications_list(
    user: bool = Query(False),
    all: bool = Query(False),
    include_archived: bool = Query(False),
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
    if not include_archived:
        query = query.where(not_(applications_table.c.is_archived))
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))

    logger.trace(f"query = {render_sql(query)}")
    return await package_response(ApplicationPartialResponse, query, pagination)


@router.get(
    "/applications/{application_identification}",
    description="Endpoint to return an application given the id",
    response_model=ApplicationResponse,
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW))],
)
async def applications_get_by_id(
    application_identification: Union[int, str] = Query(None),
):
    """
    Return the application given it's id (when int) or identifier (when str).
    """
    logger.debug(f"Getting {application_identification=}")

    if isinstance(application_identification, int):
        query = applications_table.select().where(applications_table.c.id == application_identification)
    elif isinstance(application_identification, str):
        query = applications_table.select().where(
            applications_table.c.application_identifier == application_identification
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="application_identification must be provided as int or str",
        )

    logger.trace(f"get_query = {render_sql(query)}")

    application_data = await database.fetch_one(query)
    if not application_data:
        message = f"Application {application_identification=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.trace(f"Application data: {dict(application_data)}")

    if application_data["application_uploaded"]:
        response = ApplicationResponse(
            **application_data,
            **ApplicationFiles.get_from_s3(application_data["id"]).dict(
                by_alias=True,
                exclude_defaults=True,
                exclude_unset=True,
            ),
        )
    else:
        response = ApplicationResponse(**application_data)

    return response


@router.put(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update an application given the id",
    response_model=ApplicationPartialResponse,
)
async def application_update(
    application_id: int,
    application: ApplicationUpdateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    """
    Update an application given it's id.
    """
    logger.debug(f"Preparing to update {application_id=}")
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    old_application = await _fetch_application_by_id(application_id)
    check_owner(old_application.application_owner_email, identity_claims.email, application_id, "application")

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

    return application_data


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
