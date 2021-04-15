"""
Router for the Application resource
"""
import boto3
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.config import settings
from jobbergateapi2.storage import database

S3_BUCKET = f"jobbergate-api-{settings.SERVERLESS_STAGE}-{settings.SERVERLESS_REGION}-resources"
router = APIRouter()


@router.post("/applications/", description="Endpoint for application creation")
async def applications_create(
    application_name: str = Form(...),
    application_description: str = Form(""),
    application_config: str = Form(...),
    application_file: str = Form(...),
    current_user: User = Depends(get_current_user),
    upload_file: UploadFile = File(...),
):
    """
    Endpoint used to create new applications using a user already authenticated
    """
    s3_client = boto3.client("s3")

    application = Application(
        application_name=application_name,
        application_description=application_description,
        application_file=application_file,
        application_config=application_config,
        application_owner_id=current_user.id,
    )

    async with database.transaction():
        try:
            query = applications_table.insert()
            values = {
                "application_name": application_name,
                "application_description": application_description,
                "application_owner_id": current_user.id,
                "application_file": application_file,
                "application_config": application_config,
            }
            application_created_id = await database.execute(query=query, values=values)
            application.id = application_created_id

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    application_location = (
        f"{settings.S3_BASE_PATH}/TEST/applications/{application.id}/jobbergate.tar.gz"
        # f"{S3_BASE_PATH}/{application.owner_id}/applications/{application.id}/jobbergate.tar.gz"
    )
    s3_client.put_object(
        Body=upload_file.file,
        Bucket=S3_BUCKET,
        Key=application_location,
    )
    return application


@router.delete("/applications/{application_id}", status_code=204, description="Endpoint to delete application")
async def application_delete(
    current_user: User = Depends(get_current_user),
    application_id: int = Query(..., description="id of the application to delete"),
):
    """
    Given the id of an application, delete it from the database
    """
    where_stmt = (applications_table.c.id == application_id) & (
        applications_table.c.application_owner_id == current_user.id
    )
    get_query = applications_table.select().where(where_stmt)
    application = await database.fetch_one(get_query)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found for the user with id={current_user.id}",
        )
    delete_query = applications_table.delete().where(where_stmt)
    await database.execute(delete_query)


@router.get(
    "/applications/",
    description="Endpoint to list applications",
    response_model=List[Application],
)
async def applications_get(all: Optional[bool] = Query(None), current_user: User = Depends(get_current_user)):
    """
    Endpoint to list all the applications from the authenticated user
    """
    if all:
        query = applications_table.select()
    else:
        query = applications_table.select().where(
            applications_table.c.application_owner_id == current_user.id
        )
    applications = await database.fetch_all(query)
    return applications


@router.get(
    "/applications/{application_id}",
    description="Endpoint to list applications",
)
async def applications_get_by_id(application_id: int = Query(...), current_user: User = Depends(get_current_user)):
    """
    Endpoint to list an application given it's id
    """
    query = applications_table.select().where(
        (applications_table.c.application_owner_id == current_user.id) &
        (applications_table.c.id == application_id)
    )
    raw_application = await database.fetch_one(query)
    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id=} not found for the user with id={current_user.id}",
        )

    application = Application.parse_obj(raw_application)
    return application


def include_router(app):
    app.include_router(router)
