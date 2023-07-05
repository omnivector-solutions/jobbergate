"""Router for the Job Script Template resource."""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependecies import db_session, s3_bucket
from jobbergate_api.apps.garbage_collector import garbage_collect
from jobbergate_api.apps.job_script_templates.dependecies import template_files_service, template_service
from jobbergate_api.apps.job_scripts.dependecies import job_script_files_service, job_script_service
from jobbergate_api.apps.job_scripts.tools import inject_sbatch_params, render_template_file
from jobbergate_api.apps.job_scripts.models import JobScriptFile
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptResponse,
    JobScriptUpdateRequest,
    RenderFromTemplateRequest,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.services import FileService, TableService
from jobbergate_api.security import IdentityClaims, guard

router = APIRouter(prefix="/job-scripts", tags=["Job Scripts"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for creating a stand alone job script. Use file upload to add files.",
)
async def job_script_create(
    create_request: JobScriptCreateRequest,
    service: TableService = Depends(job_script_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a stand alone job script."""
    logger.info(f"Creating a new job script with {create_request=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    new_job_script = await service.create(
        **create_request.dict(exclude_unset=True), owner_email=identity_claims.email
    )

    return new_job_script


@router.post(
    "/render-from-template/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job script creation",
)
async def job_script_create_from_template(
    create_request: JobScriptCreateRequest,
    render_request: RenderFromTemplateRequest,
    id_or_identifier: int | str = Path(...),
    session: AsyncSession = Depends(db_session),
    job_script_service: TableService = Depends(job_script_service),
    job_script_file_service: FileService = Depends(job_script_files_service),
    template_service: TableService = Depends(template_service),
    template_file_service: FileService = Depends(template_files_service),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a new job script from a job script template."""
    logger.info(f"Creating a new job script from {id_or_identifier=} with {create_request=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    if not render_request.template_output_name_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No template was selected for rendering, template_output_name_mapping is empty.",
        )

    base_template = await template_service.get(id_or_identifier)

    if not set(render_request.template_output_name_mapping.keys()).issubset(
        base_template.template_files.keys()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The required template files {} are not a subset of the template files for {}".format(
                render_request.template_output_name_mapping.keys(), id_or_identifier
            ),
        )

    job_script = await job_script_service.create(
        **create_request.dict(exclude_unset=True),
        owner_email=identity_claims.email,
        parent_template_id=base_template.id,
    )

    for i, (template_name, output_name) in enumerate(render_request.template_output_name_mapping.items()):
        file_content = await render_template_file(
            template_file_service,
            base_template.template_files[template_name],
            render_request.param_dict,
        )

        if i == 0:
            file_type = FileType.ENTRYPOINT
            if render_request.sbatch_params:
                file_content = inject_sbatch_params(file_content, render_request.sbatch_params)
        else:
            file_type = FileType.SUPPORT

        if base_template.template_files[template_name].file_type != file_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The file type {} of {} does not match the expected file type {}".format(
                    base_template.template_files[template_name].file_type, template_name, file_type
                ),
            )

        await job_script_file_service.upsert(
            id=job_script.id,
            upload_content=file_content,
            file_type=file_type,
            filename=output_name,
        )

    await session.refresh(job_script)
    return job_script


@router.get(
    "/{id}",
    description="Endpoint to return a job script by its id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_get(
    id: int = Path(),
    service: TableService = Depends(job_script_service),
):
    """Get a job script by id."""
    logger.info(f"Getting job script {id=}")

    return await service.get(id)


@router.get(
    "",
    description="Endpoint to return a list of job scripts",
    response_model=Page[JobScriptResponse],
)
async def job_script_get_list(
    user_only: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_ascending: bool = Query(True),
    from_job_script_template_id: Optional[int] = Query(
        None,
        description="Filter job-scripts by the job-script-template-id they were created from.",
    ),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW)),
    service: TableService = Depends(job_script_service),
):
    """Get a list of job scripts."""
    logger.debug("Preparing to list job scripts")

    identity_claims = IdentityClaims.from_token_payload(token_payload)

    list_kwargs = dict(
        search=search,
        sort_field=sort_field,
        sort_ascending=sort_ascending,
    )

    if user_only:
        list_kwargs["owner_email"] = identity_claims.email
    if from_job_script_template_id:
        list_kwargs["parent_template_id"] = from_job_script_template_id

    return await service.list(**list_kwargs)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script by id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_update(
    update_params: JobScriptUpdateRequest,
    id: int = Path(),
    service: TableService = Depends(job_script_service),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script {id=} with {update_params=}")
    await service.update(id, **update_params.dict(exclude_unset=True))
    return await service.get(id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script by id",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_delete(
    id: int = Path(...),
    service: TableService = Depends(job_script_service),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script {id=}")
    await service.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id}/upload/{file_name:path}",
    description="Endpoint to get a file from a job script",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_get_file(
    id: int = Path(...),
    file_name: str = Path(...),
    service: TableService = Depends(job_script_service),
    file_service: FileService = Depends(job_script_files_service),
):
    """
    Get a job script file.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script = await service.get(id)

    job_script_file = job_script.files.get(file_name)
    if not job_script_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script file {file_name=} was not found",
        )

    return StreamingResponse(
        content=file_service.file_content_generator(job_script_file),
        media_type="text/plain",
        headers={"filename": job_script_file.filename},
    )


@router.put(
    "/{id}/upload/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script file",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_upload_file(
    id: int = Path(...),
    file_type: FileType = Path(...),
    upload_file: UploadFile = File(..., description="File to upload"),
    service: TableService = Depends(job_script_service),
    file_service: FileService = Depends(job_script_files_service),
):
    """Upload a file to a job script."""
    logger.debug(f"Uploading file {upload_file.filename} to job script {id=}")
    job_script = await service.get(id)
    await file_service.upsert(
        id=job_script.id,
        upload_content=upload_file,
        filename=upload_file.filename,
        file_type=file_type,
    )


@router.delete(
    "/{id}/upload/{file_name}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file from a job script",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_delete_file(
    id: int = Path(...),
    file_name: str = Path(...),
    service: TableService = Depends(job_script_service),
    file_service: FileService = Depends(job_script_files_service),
):
    """Delete a file from a job script template by id or identifier."""
    job_script = await service.get(id)

    job_script_file = job_script.files.get(file_name)
    if job_script_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job script file {file_name=} was not found",
        )

    await file_service.delete(job_script_file)


@router.delete(
    "/upload/garbage-collector",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint to delete all unused files from the job script file storage",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
    tags=["Garbage collector"],
)
async def job_script_template_garbage_collector(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(db_session),
    bucket=Depends(s3_bucket),
):
    """Delete all unused files from job scripts on the file storage."""
    logger.info("Starting garbage collection from jobbergate file storage")
    background_tasks.add_task(
        garbage_collect,
        session,
        bucket,
        [JobScriptFile],
        background_tasks,
    )
    return {"description": "Garbage collection started"}
