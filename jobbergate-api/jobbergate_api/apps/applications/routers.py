"""
Router for the Application resource.
"""
from pathlib import PurePath
from typing import List, Optional, Union

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
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    SecureSession,
    fetch_instance,
    render_sql,
    search_clause,
    secure_session,
    sort_clause,
)

router = APIRouter()


async def _fetch_application_by_id(
    secure_session: SecureSession, application_id: int
) -> ApplicationPartialResponse:
    """
    Fetch an application from the database by its id.
    """
    return await fetch_instance(
        secure_session.session,
        application_id,
        applications_table,
        ApplicationPartialResponse,
    )


def _get_override_bucket_name(secure_session: SecureSession) -> Optional[str]:
    """
    Get the override_bucket_name based on organization_id if multi-tenancy is enabled.
    """
    if settings.MULTI_TENANCY_ENABLED:
        return secure_session.identity_payload.organization_id
    return None


@router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationPartialResponse,
    description="Endpoint for application creation",
)
async def applications_create(
    application: ApplicationCreateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """
    Create new applications using an authenticated user token.
    """
    logger.debug(f"Creating {application=}")

    create_dict = dict(
        **application.dict(exclude_unset=True),
        application_owner_email=secure_session.identity_payload.email,
    )

    logger.debug("Inserting application")

    try:
        insert_query = applications_table.insert().values(**create_dict).returning(applications_table)

        logger.debug(f"insert_query = {render_sql(secure_session.session, insert_query)}")
        raw_data = await secure_session.session.execute(insert_query)
        application_data = raw_data.one()

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
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
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

    application = await _fetch_application_by_id(secure_session, application_id)
    check_owner(
        application.application_owner_email,
        secure_session.identity_payload.email,
        application_id,
        "application",
    )

    ApplicationFiles.get_from_upload_files(upload_files).write_to_s3(
        application_id,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=True))
    )

    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")
    await secure_session.session.execute(update_query)


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
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """Update the application files individually."""
    application = await _fetch_application_by_id(secure_session, application_id)
    check_owner(
        application.application_owner_email,
        secure_session.identity_payload.email,
        application_id,
        "application",
    )

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
    ).write_to_s3(
        application_id,
        remove_previous_files=False,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications/{application_id}/upload",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint for deleting application files",
)
async def applications_delete_upload(
    application_id: int = Query(..., description="id of the application for which to delete the file"),
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """
    Delete application files using an authenticated user token.
    """
    logger.debug(f"Preparing to delete files for {application_id=}")

    application = await _fetch_application_by_id(secure_session, application_id)
    check_owner(
        application.application_owner_email,
        secure_session.identity_payload.email,
        application_id,
        "application",
    )

    if not application.application_uploaded:
        logger.debug(f"Trying to delete an applications that was not uploaded ({application_id=})")
        return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)

    ApplicationFiles.delete_from_s3(
        application_id,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(dict(application_uploaded=False))
    )

    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")
    await secure_session.session.execute(update_query)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application",
)
async def application_delete(
    application_id: int = Query(..., description="id of the application to delete"),
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """
    Delete application from the database and S3 given its id.
    """
    application = await _fetch_application_by_id(secure_session, application_id)
    check_owner(
        application.application_owner_email,
        secure_session.identity_payload.email,
        application_id,
        "application",
    )

    logger.debug(f"Orphaning job_scripts rendered from application {application_id=}")
    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.application_id == application_id)
        .values(dict(application_id=None))
    )
    logger.debug(f"update_query = {render_sql(secure_session.session, update_query)}")
    await secure_session.session.execute(update_query)

    logger.debug(f"Preparing to delete {application_id=} from the database and S3")
    delete_query = applications_table.delete().where(applications_table.c.id == application_id)
    logger.trace(f"delete_query = {render_sql(secure_session.session, delete_query)}")
    await secure_session.session.execute(delete_query)

    ApplicationFiles.delete_from_s3(
        application_id,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/applications",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application by identifier",
)
async def application_delete_by_identifier(
    identifier: str = Query(..., description="identifier of the application to delete"),
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """
    Delete application from the database and S3 given it's identifier.
    """
    logger.debug(f"Preparing to delete {identifier=} from the database and S3")

    where_stmt = applications_table.c.application_identifier == identifier
    get_query = applications_table.select().where(where_stmt)
    logger.trace(f"get_query = {render_sql(secure_session.session, get_query)}")

    raw_result = await secure_session.session.execute(get_query)
    raw_application = raw_result.one_or_none()
    if not raw_application:
        message = f"Application {identifier=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )
    application = ApplicationPartialResponse.from_orm(raw_application)

    check_owner(
        application.application_owner_email,
        secure_session.identity_payload.email,
        application.id,
        "application",
    )

    delete_query = applications_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(secure_session.session, delete_query)}")

    await secure_session.session.execute(delete_query)

    ApplicationFiles.delete_from_s3(
        application.id,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

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
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_VIEW)),
):
    """
    List all applications.
    """
    logger.debug("Preparing to list the Applications")

    query = applications_table.select()
    if user:
        query = query.where(
            applications_table.c.application_owner_email == secure_session.identity_payload.email
        )
    if not all:
        query = query.where(not_(applications_table.c.application_identifier.is_(None)))
    if not include_archived:
        query = query.where(not_(applications_table.c.is_archived))
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))

    logger.trace(f"query = {render_sql(secure_session.session, query)}")
    return await package_response(secure_session.session, ApplicationPartialResponse, query, pagination)


@router.get(
    "/applications/{application_identification}",
    description="Endpoint to return an application given the id",
    response_model=ApplicationResponse,
)
async def applications_get_by_id(
    application_identification: Union[int, str] = Query(None),
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_VIEW)),
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

    logger.trace(f"get_query = {render_sql(secure_session.session, query)}")

    raw_result = await secure_session.session.execute(query)
    application_data = raw_result.one_or_none()

    if not application_data:
        message = f"Application {application_identification=} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    application = ApplicationResponse.from_orm(application_data)

    if application.application_uploaded:
        application_files = ApplicationFiles.get_from_s3(
            application.id,
            override_bucket_name=_get_override_bucket_name(secure_session),
        )
        application.application_config = application_files.config_file
        application.application_source_file = application_files.source_file
        application.application_templates = application_files.templates

    return application


@router.put(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update an application given the id",
    response_model=ApplicationPartialResponse,
)
async def application_update(
    application_id: int,
    application: ApplicationUpdateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.APPLICATIONS_EDIT)),
):
    """
    Update an application given it's id.
    """
    logger.debug(f"Preparing to update {application_id=}")
    old_application = await _fetch_application_by_id(secure_session, application_id)
    check_owner(
        old_application.application_owner_email,
        secure_session.identity_payload.email,
        application_id,
        "application",
    )

    update_query = (
        applications_table.update()
        .where(applications_table.c.id == application_id)
        .values(application.dict(exclude_unset=True))
        .returning(applications_table)
    )
    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")

    try:
        raw_result = await secure_session.session.execute(update_query)

    except INTEGRITY_CHECK_EXCEPTIONS as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    application_data = raw_result.one()
    return application_data


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
