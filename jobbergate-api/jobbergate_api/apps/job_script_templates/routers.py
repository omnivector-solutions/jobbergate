"""Router for the Job Script Template resource."""

from fastapi import APIRouter, Depends, status

from jobbergate_api.apps.job_script_templates.dependecies import create
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateResponse
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.security import guard

router = APIRouter()


@router.post(
    "/job-script-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateResponse,
    description="Endpoint for application creation",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_template_create(
    new_job_template: JobTemplateResponse = Depends(create),
):
    return new_job_template


async def job_script_template_get_one():
    pass


async def job_script_template_get_list():
    pass


async def job_script_template_update():
    pass


async def job_script_template_delete():
    pass


async def job_script_template_get_file():
    pass


async def job_script_template_upload_file():
    pass


async def job_script_template_delete_file():
    pass
