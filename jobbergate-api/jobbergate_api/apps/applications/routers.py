"""
Router for the Application resource.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import not_

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import Application, ApplicationRequest
from jobbergate_api.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergate_api.pagination import Pagination, Response, package_response
from jobbergate_api.s3_manager import S3Manager
from jobbergate_api.security import ArmadaClaims, guard
from jobbergate_api.storage import database

router = APIRouter()
s3man = S3Manager()


@router.post(
    "/applications/", status_code=status.HTTP_201_CREATED, description="Endpoint for application creation",
)
async def applications_create(
    application_name: str = Form(...),
    application_identifier: Optional[str] = Form(None),
    application_description: str = Form(""),
    application_config: str = Form(...),
    application_file: str = Form(...),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:applications:create")),
    upload_file: UploadFile = File(...),
):
    """
    Create new applications using an authenticated user token.
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    application = ApplicationRequest(
        application_name=application_name,
        application_identifier=application_identifier,
        application_description=application_description,
        application_file=application_file,
        application_config=application_config,
        application_owner_email=armada_claims.user_email,
    )

    async with database.transaction():
        try:
            query = applications_table.insert()
            values = application.dict()
            application_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    s3man.put(upload_file, app_id=application_created_id)

    return Application(id=application_created_id, **application.dict())


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
    await database.execute(delete_query)
    s3man.delete(app_id=str(application_id))


@router.get(
    "/applications/", description="Endpoint to list applications", response_model=Response[Application],
)
async def applications_list(
    pagination: Pagination = Depends(),
    user: Optional[bool] = Query(None),
    all: Optional[bool] = Query(None),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:applications:read")),
):
    """
    List all applications
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    query = applications_table.select()
    if user:
        query = query.where(applications_table.c.application_owner_email == armada_claims.user_email)
    if all is None:
        query = query.where(not_(applications_table.c.application_identifier.is_(None)))
    return await package_response(Application, query, pagination)


@router.get(
    "/applications/{application_id}",
    description="Endpoint to return an application given the id",
    response_model=Application,
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
    application = Application.parse_obj(raw_application)

    return application


@router.put(
    "/applications/{application_id}",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to update an application given the id",
    response_model=Application,
)
async def application_update(
    application_id: int = Query(...),
    application_name: Optional[str] = Form(None),
    application_identifier: Optional[str] = Form(None),
    application_description: Optional[str] = Form(None),
    application_config: Optional[str] = Form(None),
    application_file: Optional[str] = Form(None),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:applications:update")),
    upload_file: Optional[UploadFile] = File(None),
):
    """
    Update an application given it's id.
    """
    query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id=} not found.",
        )

    update_dict: Dict[str, Any] = {}
    if application_name:
        update_dict["application_name"] = application_name
    if application_identifier:
        update_dict["application_identifier"] = application_identifier
    if application_description:
        update_dict["application_description"] = application_description
    if application_file:
        update_dict["application_file"] = application_file
    if application_config:
        update_dict["application_config"] = application_config
    update_dict["updated_at"] = datetime.utcnow()

    q_update = (
        applications_table.update().where(applications_table.c.id == application_id).values(update_dict)
    )
    async with database.transaction():
        try:
            await database.execute(q_update)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    query = applications_table.select().where(applications_table.c.id == application_id)
    application = Application.parse_obj(await database.fetch_one(query))

    if upload_file:
        s3man.put(upload_file, app_id=str(application_id))

    return application


def include_router(app):
    app.include_router(router)
