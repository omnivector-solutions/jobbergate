"""Router for the Job Script Template resource."""
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from loguru import logger

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependecies import file_services, s3_bucket, secure_services
from jobbergate_api.apps.garbage_collector import garbage_collect
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_script_templates.services import crud_service as template_crud_service
from jobbergate_api.apps.job_script_templates.services import template_file_service
from jobbergate_api.apps.job_scripts.models import JobScriptFile
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptResponse,
    JobScriptUpdateRequest,
    RenderFromTemplateRequest,
)
from jobbergate_api.apps.job_scripts.services import crud_service, file_service
from jobbergate_api.apps.job_scripts.tools import inject_sbatch_params
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import SecureSession, secure_session

router = APIRouter(prefix="/job-scripts", tags=["Job Scripts"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for creating a stand alone job script. Use file upload to add files.",
)
async def job_script_create(
    create_request: JobScriptCreateRequest,
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, services=[crud_service])
    ),
):
    """Create a stand alone job script."""
    logger.info(f"Creating a new job script with {create_request=}")

    if secure_session.identity_payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    new_job_script = await crud_service.create(
        owner_email=secure_session.identity_payload.email,
        **create_request.dict(exclude_unset=True),
    )

    return new_job_script


@router.post(
    "/render-from-template/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job script creation",
    dependencies=[Depends(file_services(file_service, template_file_service))],
)
async def job_script_create_from_template(
    create_request: JobScriptCreateRequest,
    render_request: RenderFromTemplateRequest,
    id_or_identifier: int | str = Path(...),
    secure_session: SecureSession = Depends(
        secure_services(
            Permissions.JOB_SCRIPTS_EDIT,
            services=[crud_service, template_crud_service, file_service, template_file_service],
        )
    ),
):
    """Create a new job script from a job script template."""
    logger.info(f"Creating a new job script from {id_or_identifier=} with {create_request=}")

    if secure_session.identity_payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    base_template = cast(JobScriptTemplate, await template_crud_service.get(id_or_identifier))

    required_map = render_request.template_output_name_mapping
    entrypoint_key = list(required_map.values())[0]

    required_keys = set(required_map.keys())
    provided_keys = set(f.filename for f in base_template.template_files)
    missing_keys = required_keys - provided_keys
    if len(missing_keys) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"The template files are missing required files: {missing_keys} for {id_or_identifier}"),
        )

    mapped_template_files = {
        new_filename: file
        for file in base_template.template_files
        if (new_filename := required_map.get(file.filename, None))
    }

    job_script = await crud_service.create(
        owner_email=secure_session.identity_payload.email,
        parent_template_id=base_template.id,
        **create_request.dict(exclude_unset=True),
    )

    for new_filename, template_file in mapped_template_files.items():
        file_content = await template_file_service.render(
            template_file,
            render_request.param_dict,
        )

        if new_filename == entrypoint_key:
            file_type = FileType.ENTRYPOINT
            if render_request.sbatch_params:
                file_content = inject_sbatch_params(file_content, render_request.sbatch_params)
        else:
            file_type = FileType.SUPPORT

        if template_file.file_type != file_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The file type {template_file} does not match the expected file type {file_type}",
            )

        await file_service.upsert(
            parent_id=job_script.id,
            filename=new_filename,
            upload_content=file_content,
            file_type=file_type,
        )

    await secure_session.session.refresh(job_script)
    return job_script


@router.get(
    "/{id}",
    description="Endpoint to return a job script by its id",
    response_model=JobScriptResponse,
    dependencies=[Depends(secure_services(Permissions.JOB_SCRIPTS_VIEW, services=[crud_service]))],
)
async def job_script_get(id: int = Path()):
    """Get a job script by id."""
    logger.info(f"Getting job script {id=}")
    return await crud_service.get(id)


@router.get(
    "",
    description="Endpoint to return a list of job scripts",
    response_model=Page[JobScriptResponse],
)
async def job_script_get_list(
    user_only: bool = Query(False),
    include_archived: bool = Query(False),
    search: str | None = Query(None),
    sort_field: str | None = Query(None),
    sort_ascending: bool = Query(True),
    from_job_script_template_id: int
    | None = Query(
        None,
        description="Filter job-scripts by the job-script-template-id they were created from.",
    ),
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SCRIPTS_VIEW, services=[crud_service])
    ),
):
    """Get a list of job scripts."""
    logger.debug("Preparing to list job scripts")

    list_kwargs: dict[str, Any] = dict(
        search=search,
        sort_field=sort_field,
        sort_ascending=sort_ascending,
        include_archived=include_archived,
    )

    if user_only:
        list_kwargs["owner_email"] = secure_session.identity_payload.email
    if from_job_script_template_id:
        list_kwargs["parent_template_id"] = from_job_script_template_id

    return await crud_service.paginated_list(**list_kwargs)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script by id",
    response_model=JobScriptResponse,
    dependencies=[Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT, services=[crud_service]))],
)
async def job_script_update(
    update_params: JobScriptUpdateRequest,
    id: int = Path(),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script {id=} with {update_params=}")
    return await crud_service.update(id, **update_params.dict(exclude_unset=True))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script by id",
    dependencies=[Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT, services=[crud_service]))],
)
async def job_script_delete(
    id: int = Path(...),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script {id=}")
    await crud_service.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id}/upload/{file_name:path}",
    description="Endpoint to get a file from a job script",
    dependencies=[
        Depends(secure_services(Permissions.JOB_SCRIPTS_VIEW, services=[crud_service, file_service])),
        Depends(file_services(file_service)),
    ],
)
async def job_script_get_file(
    id: int = Path(...),
    file_name: str = Path(...),
):
    """
    Get a job script file.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script = await crud_service.get(id)
    job_script_file = await file_service.get(job_script.id, file_name)
    return StreamingResponse(
        content=await file_service.stream_file_content(job_script_file),
        media_type="text/plain",
        headers={"filename": job_script_file.filename},
    )


@router.put(
    "/{id}/upload/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script file",
    dependencies=[
        Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT, services=[crud_service, file_service])),
        Depends(file_services(file_service)),
    ],
)
async def job_script_upload_file(
    id: int = Path(...),
    file_type: FileType = Path(...),
    upload_file: UploadFile = File(..., description="File to upload"),
):
    """Upload a file to a job script."""
    if upload_file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The upload file has no filename",
        )

    logger.debug(f"Uploading file {upload_file.filename} to job script {id=}")
    job_script = await crud_service.get(id)
    await file_service.upsert(
        parent_id=job_script.id,
        filename=upload_file.filename,
        upload_content=upload_file,
        file_type=file_type,
    )


@router.delete(
    "/{id}/upload/{file_name}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file from a job script",
    dependencies=[
        Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT, services=[crud_service, file_service])),
        Depends(file_services(file_service)),
    ],
)
async def job_script_delete_file(
    id: int = Path(...),
    file_name: str = Path(...),
):
    """Delete a file from a job script template by id or identifier."""
    job_script = await crud_service.get(id)
    job_script_file = await file_service.get(job_script.id, file_name)
    await file_service.delete(job_script_file)


@router.delete(
    "/upload/garbage-collector",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint to delete all unused files from the job script file storage",
    tags=["Garbage collector"],
)
async def job_script_template_garbage_collector(
    background_tasks: BackgroundTasks,
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
    bucket=Depends(s3_bucket),
):
    """Delete all unused files from job scripts on the file storage."""
    logger.info("Starting garbage collection from jobbergate file storage")
    background_tasks.add_task(
        garbage_collect,
        secure_session.session,
        bucket,
        [JobScriptFile],
        background_tasks,
    )
    return {"description": "Garbage collection started"}
