"""
Router for the Application resource
"""
import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.config import settings
from jobbergateapi2.storage import database

S3_BUCKET = f"jobbergate-api-{settings.SERVERLESS_STAGE}-{settings.SERVERLESS_REGION}-resources"
router = APIRouter()


@router.post("/application", description="Endpoint for application creation")
async def applications_create(
    application_name: str = Form(None),
    application_description: str = Form(""),
    application_config: str = Form(""),
    application_file: str = Form(""),
    current_user: User = Depends(get_current_user),
    upload_file: UploadFile = File(None),
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


def include_router(app):
    app.include_router(router)
