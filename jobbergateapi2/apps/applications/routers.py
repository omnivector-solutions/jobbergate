"""
Router for the Application resource.
"""
from datetime import datetime
from typing import List, Optional

import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application, ApplicationRequest
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.config import settings
from jobbergateapi2.pagination import Pagination
from jobbergateapi2.storage import database
from jobbergateapi2.security import armasec_factory

S3_BUCKET = f"jobbergateapi2-{settings.SERVERLESS_STAGE}-{settings.SERVERLESS_REGION}-resources"
router = APIRouter()


read_permission = armasec_factory(scopes=["applications:read"])
create_permission = armasec_factory(scopes=["applications:create"])
create_permission = armasec_factory(scopes=["applications:create"])


async def applications_acl_as_list():
    """
    Return the permissions as list for the Application resoruce.
    """
    return await resource_acl_as_list("application")


@router.post(
    "/applications/",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for application creation",
)
async def applications_create(
    application_name: str = Form(...),
    application_description: str = Form(""),
    application_config: str = Form(...),
    application_file: str = Form(...),
    token_payload: TokenPayload = Depends(armasec_factory("jobbergate:applicaitons:create")),
    upload_file: UploadFile = File(...),
):
    """
    Create new applications using an authenticated user token.
    """
    s3_client = boto3.client("s3")

    application = ApplicationRequest(
        application_name=application_name,
        application_description=application_description,
        application_file=application_file,
        application_config=application_config,
        application_owner_id=token_payload.sub,
    )

    async with database.transaction():
        try:
            query = applications_table.insert()
            values = application.dict()
            application_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    application_location = f"{base}/{owner_id}/applications/{app_id}/jobbergate.tar.gz".format(
        base=settings.S3_BASE_PATH,
        owner_id=application.application_owner_id,
        app_id=application_created_id,
    )
    s3_client.put_object(
        Body=upload_file.file,
        Bucket=S3_BUCKET,
        Key=application_location,
    )
    return Application(id=application_created_id, **application.dict())


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application",
    dependencies=[Depends(armasec_factory("jobbergate:applicaitons:delete"))],
)
async def application_delete(
    application_id: int = Query(..., description="id of the application to delete"),
):
    """
    Delete application from the database and S3 given it's id.
    """
    s3_client = boto3.client("s3")
    where_stmt = applications_table.c.id == application_id
    get_query = applications_table.select().where(where_stmt)
    raw_application = await database.fetch_one(get_query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
        )
    application = Application.parse_obj(raw_application)
    delete_query = applications_table.delete().where(where_stmt)
    await database.execute(delete_query)
    application_location = f"{base}/{owner_id}/applications/{app_id}/jobbergate.tar.gz".format(
        base=settings.S3_BASE_PATH,
        owner_id=application.application_owner_id,
        app_id=application_created_id,
    )
    s3_client.delete_object(
        Bucket=S3_BUCKET,
        Key=application_location,
    )


@router.get(
    "/applications/",
    description="Endpoint to list applications",
    response_model=List[Application],
    dependencies=[Depends(armasec_factory("jobbergate:applicaitons:read"))],
)
async def applications_list(p: Pagination = Depends(), all: Optional[bool] = Query(None)):
    """
    List all applications
    """
    query = applications_table.select()
    if not all:
        query = query.where(applications_table.c.application_owner_id == tokn.sub)
    query = query.limit(p.limit).offset(p.skip)
    raw_applications = await database.fetch_all(query)
    applications = [Application.parse_obj(x) for x in raw_applications]
    return applications


@router.get(
    "/applications/{application_id}",
    description="Endpoint to return an application given the id",
    response_model=Application,
    dependencies=[Depends(armasec_factory("jobbergate:applicaitons:read"))],
)
async def applications_get_by_id(application_id: int = Query(...)):
    """
    Return the application given it's id.
    """
    query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
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
    application_description: Optional[str] = Form(None),
    application_config: Optional[str] = Form(None),
    application_file: Optional[str] = Form(None),
    token_payload: TokenPayload = Depends(armasec_factory("jobbergate:applicaitons:update")),
    upload_file: Optional[UploadFile] = File(None),
):
    """
    Update an application given it's id.
    """
    s3_client = boto3.client("s3")

    query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found.",
        )

    update_dict = {}
    if application_name:
        update_dict["application_name"] = application_name
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
    application_location = f"{base}/{owner_id}/applications/{app_id}/jobbergate.tar.gz".format(
        base=settings.S3_BASE_PATH,
        # owner_id=token_payload.sub,
        owner_id=application.application_owner_id,
        app_id=application_created_id,
    )
    if upload_file:
        s3_client.put_object(
            Body=upload_file.file,
            Bucket=S3_BUCKET,
            Key=application_location,
        )
    query = applications_table.select().where(applications_table.c.id == application_id)
    application = Application.parse_obj(await database.fetch_one(query))
    return application


def include_router(app):
    app.include_router(router)
