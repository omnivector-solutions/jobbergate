"""Router for the Job Script Template resource."""
from armasec import TokenPayload
from fastapi import APIRouter, Depends, File, HTTPException, Path
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError, NoResultFound

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.dependecies import template_files_service, template_service
from jobbergate_api.apps.job_script_templates.service import (
    JobScriptTemplateFilesService,
    JobScriptTemplateService,
)
from jobbergate_api.apps.job_scripts.dependecies import job_script_files_service, job_script_service
from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_scripts.schemas import (
    RenderFromTemplateRequest,
    JobScriptCreateRequest,
    JobScriptResponse,
    JobScriptUpdateRequest,
)
from jobbergate_api.apps.job_scripts.service import JobScriptFilesService, JobScriptService
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.security import IdentityClaims, guard

router = APIRouter(prefix="/job-scripts", tags=["Job Scripts"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job script creation",
)
async def job_script_create(
    create_request: JobScriptCreateRequest,
    service: JobScriptService = Depends(job_script_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a new job script template."""
    logger.info(f"Creating a new job script with {create_request=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    new_job_script = await service.create(create_request, identity_claims.email)

    return new_job_script


@router.post(
    "/render-template/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job script creation",
)
async def job_script_create_from_template(
    create_request: JobScriptCreateRequest,
    render_request: RenderFromTemplateRequest,
    id_or_identifier: int | str = Path(...),
    job_script_service: JobScriptService = Depends(job_script_service),
    job_script_file_service: JobScriptFilesService = Depends(job_script_files_service),
    template_service: JobScriptTemplateService = Depends(template_service),
    template_file_service: JobScriptTemplateFilesService = Depends(template_files_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a new job script template."""
    logger.info(f"Creating a new job script from {id_or_identifier=} with {create_request=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    base_template = await template_service.get(id_or_identifier)
    if base_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    # entrypoint_file =

    job_script = await job_script_service.create(create_request, identity_claims.email)

    return job_script


@router.get(
    "/{id}",
    description="Endpoint to return a job script by its id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_get(
    id: int = Path(),
    service: JobScriptService = Depends(job_script_service),
):
    """Get a job script by id."""
    logger.info(f"Getting job script {id=}")
    result = await service.get(id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )
    return result


async def job_script_get_list():
    pass


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script by id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_update(
    update_request: JobScriptUpdateRequest,
    id: int = Path(),
    service: JobScriptService = Depends(job_script_service),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script {id=}")
    try:
        result = await service.update(id, update_request)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )
    return result


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script by id",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_delete(
    id: int = Path(...),
    service: JobScriptService = Depends(job_script_service),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script {id=}")
    try:
        await service.delete(id)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id}/upload/{file_name}",
    description="Endpoint to get a file from a job script",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_get_file(
    id: int = Path(...),
    file_name: str = Path(...),
    service: JobScriptService = Depends(job_script_service),
    file_service: JobScriptFilesService = Depends(job_script_files_service),
):
    """
    Get a job script file.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script = await service.get(id)
    if job_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )

    job_script_file_list = [f for f in job_script.files if f.filename == file_name]
    if not job_script_file_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script file {file_name=} was not found",
        )

    job_script_file = job_script_file_list[0]

    return StreamingResponse(content=file_service.get(job_script_file), media_type="text/plain")


@router.put(
    "/{id}/upload/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script file",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_upload_file(
    id: int = Path(...),
    file_type: FileType = Path(...),
    upload_file: UploadFile = File(..., description="File to upload"),
    service: JobScriptService = Depends(job_script_service),
    file_service: JobScriptFilesService = Depends(job_script_files_service),
):
    """Upload a file to a job script."""
    job_script = await service.get(id)
    if job_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )
    await file_service.upsert(job_script.id, file_type, upload_file)


@router.delete(
    "/{id}/upload/{file_name}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file from a job script",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_delete_file(
    id: int = Path(...),
    file_name: str = Path(...),
    service: JobScriptService = Depends(job_script_service),
    file_service: JobScriptFilesService = Depends(job_script_files_service),
):
    """Delete a file from a job script template by id or identifier."""
    job_script = await service.get(id)
    if job_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script {id=} was not found",
        )

    job_script_file_list = [f for f in job_script.files if f.filename == file_name]
    if not job_script_file_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script file {file_name=} was not found",
        )

    job_script_file = job_script_file_list[0]

    await file_service.delete(job_script_file)
