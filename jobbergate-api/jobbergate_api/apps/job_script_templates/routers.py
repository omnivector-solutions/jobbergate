"""Router for the Job Script Template resource."""

from armasec import TokenPayload
from fastapi import APIRouter, Depends, status

from jobbergate_api.apps.job_script_templates.dependecies import template_service
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest, JobTemplateResponse
from jobbergate_api.apps.job_script_templates.service import JobScriptTemplateService
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.security import IdentityClaims, guard

router = APIRouter(prefix="/job-script-templates")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateResponse,
    description="Endpoint for application creation",
)
async def job_script_template_create(
    create_request: JobTemplateCreateRequest,
    service: JobScriptTemplateService = Depends(template_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    identity_claims = IdentityClaims.from_token_payload(token_payload)

    return await service.create(create_request, identity_claims.email)


@router.get(
    "/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateResponse,
    description="Endpoint for application creation",
)
async def job_script_template_get_one_by_id():
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
