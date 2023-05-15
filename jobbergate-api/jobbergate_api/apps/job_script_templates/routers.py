"""Router for the Job Script Template resource."""
from typing import Any

from armasec import TokenPayload
from fastapi import APIRouter, Body, Depends, File, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError, NoResultFound

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.dependecies import (
    template_files_service,
    template_service,
    workflow_files_service,
)
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateResponse,
    JobTemplateUpdateRequest,
)
from jobbergate_api.apps.job_script_templates.service import (
    JobScriptTemplateFilesService,
    JobScriptTemplateService,
    WorkflowFilesService,
)
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
    """Create a new job script template."""
    logger.info(f"Creating a new job script template with {create_request=}")

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
    id_or_identifier: int | str = Query(...),
    service: JobScriptTemplateService = Depends(template_service),
):
    """Get a job script template by id or identifier."""
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
    logger.info(f"Updating job script template {id_or_identifier=} with {update_request=}")
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
    try:
        await service.delete(id_or_identifier)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id_or_identifier}/upload/template/{file_name}",
    description="Endpoint to get a file from a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW))],
)
async def job_script_template_get_file(
    id_or_identifier: int | str = Query(None),
    file_name: str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: JobScriptTemplateFilesService = Depends(template_files_service),
):
    """
    Get a job script template file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script_template = await service.get(id_or_identifier)
    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    job_script_template_file_list = [f for f in job_script_template.template_files if f.filename == file_name]
    if not job_script_template_file_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template file with {file_name=} was not found",
        )

    job_script_template_file = job_script_template_file_list[0]

    return StreamingResponse(content=file_service.get(job_script_template_file), media_type="text/plain")


@router.put(
    "/{id_or_identifier}/upload/template/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_template_upload_file(
    id_or_identifier: int | str = Query(None),
    file_type: FileType = Query(None),
    upload_file: UploadFile = File(..., description="File to upload"),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: JobScriptTemplateFilesService = Depends(template_files_service),
):
    """Upload a file to a job script template by id or identifier."""
    logger.debug(f"Uploading file {upload_file.filename} to job script template {id_or_identifier=}")
    job_script_template = await service.get(id_or_identifier)
    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )
    await file_service.upsert(job_script_template.id, file_type, upload_file)


@router.delete(
    "/{id_or_identifier}/upload/template/{file_name}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file to a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_template_delete_file(
    id_or_identifier: int | str = Query(None),
    file_name: str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: JobScriptTemplateFilesService = Depends(template_files_service),
):
    """Delete a file from a job script template by id or identifier."""
    job_script_template = await service.get(id_or_identifier)
    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    job_script_template_file_list = [f for f in job_script_template.template_files if f.filename == file_name]
    if not job_script_template_file_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template file with {file_name=} was not found",
        )

    job_script_template_file = job_script_template_file_list[0]

    await file_service.delete(job_script_template_file)


@router.get(
    "/{id_or_identifier}/upload/workflow",
    description="Endpoint to get a workflow file from a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_VIEW))],
)
async def job_script_workflow_get_file(
    id_or_identifier: int | str = Query(None),
    file_name: str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: WorkflowFilesService = Depends(workflow_files_service),
):
    """
    Get a workflow file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script_template = await service.get(id_or_identifier)
    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    workflow_file = job_script_template.workflow_file
    if not workflow_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow file with {file_name=} was not found",
        )

    return StreamingResponse(
        content=file_service.get(workflow_file),
        media_type="text/plain",
        headers={"filename": WORKFLOW_FILE_NAME},
    )


@router.put(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_workflow_upload_file(
    id_or_identifier: int | str = Query(None),
    upload_file: UploadFile = File(..., description="File to upload"),
    runtime_config: dict[str, Any] | None = Body(None, description="Runtime configuration"),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: WorkflowFilesService = Depends(workflow_files_service),
):
    """Upload a file to a job script workflow by id or identifier."""
    job_script_template = await service.get(id_or_identifier)

    if runtime_config is None:
        runtime_config = {}

    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )
    await file_service.upsert(job_script_template.id, runtime_config, upload_file)


@router.delete(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a workflow file from a job script template by id or identifier",
    dependencies=[Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT))],
)
async def job_script_workflow_delete_file(
    id_or_identifier: int | str = Query(None),
    service: JobScriptTemplateService = Depends(template_service),
    file_service: WorkflowFilesService = Depends(workflow_files_service),
):
    """Delete a workflow file from a job script template by id or identifier."""
    job_script_template = await service.get(id_or_identifier)
    if job_script_template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script template with {id_or_identifier=} was not found",
        )

    workflow_file = job_script_template.workflow_file
    if not workflow_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow file with was not found for {id_or_identifier=}",
        )

    await file_service.delete(workflow_file)
