"""Router for the Job Script Template resource."""
from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import status
from loguru import logger
from sqlalchemy.exc import IntegrityError, NoResultFound

from jobbergate_api.apps.job_script_templates.dependecies import template_service
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateResponse,
    JobTemplateUpdateRequest,
)
from jobbergate_api.apps.job_script_templates.service import JobScriptTemplateService
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.security import IdentityClaims, guard

router = APIRouter(prefix="/job-script-templates")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateResponse,
    description="Endpoint for job script template creation",
)
async def job_script_template_create(
    create_request: JobTemplateCreateRequest,
    service: JobScriptTemplateService = Depends(template_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
):
    logger.info(f"Creating a new job script template with {JobTemplateCreateRequest=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    try:
        new_job_template = await service.create(create_request, identity_claims.email)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job script template with the same identifier already exists",
        )
    return new_job_template


@router.get(
    "/{id_or_identifier}",
    description="Endpoint to return a job script template by its id or identifier",
    response_model=JobTemplateResponse,
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW))],
)
async def job_script_template_get(
    id_or_identifier: int | str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
):
    logger.info(f"Getting job script template with {id_or_identifier=}")
    result = await service.get(id_or_identifier)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )
    return result


async def job_script_template_get_list():
    pass


@router.put(
    "/{id_or_identifier}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script template by id or identifier",
    response_model=JobTemplateResponse,
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_template_update(
    update_request: JobTemplateUpdateRequest,
    id_or_identifier: int | str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script template with {id_or_identifier=}")
    try:
        result = await service.update(id_or_identifier, update_request)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )
    return result


@router.delete(
    "/{id_or_identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_template_delete(
    id_or_identifier: int | str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script template with {id_or_identifier=}")
    await service.delete(id_or_identifier)

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


async def job_script_template_get_file():
    pass


async def job_script_template_upload_file():
    pass


async def job_script_template_delete_file():
    pass
