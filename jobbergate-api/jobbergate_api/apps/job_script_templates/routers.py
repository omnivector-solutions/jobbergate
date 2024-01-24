"""Router for the Job Script Template resource."""

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from loguru import logger
from sqlalchemy.exc import IntegrityError

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.garbage_collector import garbage_collect
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplateFile, WorkflowFile
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCloneRequest,
    JobTemplateCreateRequest,
    JobTemplateDetailedView,
    JobTemplateListView,
    JobTemplateUpdateRequest,
    RunTimeConfig,
    TemplateFileDetailedView,
    WorkflowFileDetailedView,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.schemas import ListParams
from jobbergate_api.apps.services import ServiceError

router = APIRouter(prefix="/job-script-templates", tags=["Job Script Templates"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateDetailedView,
    description="Endpoint for job script template creation",
)
async def job_script_template_create(
    create_request: JobTemplateCreateRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Create a new job script template."""
    logger.info(f"Creating a new job script template with {create_request=}")

    try:
        return await secure_services.crud.template.create(
            owner_email=secure_services.identity_payload.email,
            **create_request.dict(exclude_unset=True),
        )
    except IntegrityError:
        message = f"Job script template with the identifier={create_request.identifier} already exists"
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


@router.get(
    "/{id_or_identifier}",
    description="Endpoint to return a job script template by its id or identifier",
    response_model=JobTemplateDetailedView,
)
async def job_script_template_get(
    id_or_identifier: int | str = Path(),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_TEMPLATES_VIEW, commit=False)),
):
    """Get a job script template by id or identifier."""
    logger.info(f"Getting job script template with {id_or_identifier=}")
    return await secure_services.crud.template.get(id_or_identifier, include_files=True)


@router.post(
    "/clone/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateDetailedView,
    description="Endpoint for cloning a job script template to a new entry owned by the user",
)
async def job_script_template_clone(
    id_or_identifier: int | str = Path(),
    clone_request: JobTemplateCloneRequest | None = None,
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Clone a job script template by id or identifier."""
    logger.info(f"Cloning a job script template from {id_or_identifier=} with {clone_request=}")

    if clone_request is None:
        clone_request = JobTemplateCloneRequest()

    original_instance = await secure_services.crud.template.get(id_or_identifier, include_files=True)

    # Identifier is specifically set to None to avoid conflicts with the original instance
    new_data = {"identifier": None, **clone_request.dict(exclude_unset=True)}
    try:
        cloned_instance = await secure_services.crud.template.clone_instance(
            original_instance,
            owner_email=secure_services.identity_payload.email,
            **new_data,
        )
    except IntegrityError:
        message = "Job script template with the identifier={} already exists".format(
            clone_request.identifier or original_instance.identifier
        )
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)

    for file in original_instance.template_files:
        await secure_services.file.template.clone_instance(file, cloned_instance.id)
    for file in original_instance.workflow_files:
        await secure_services.file.workflow.clone_instance(file, cloned_instance.id)

    # Get again to update the file data
    return await secure_services.crud.template.get(cloned_instance.id, include_files=True)


@router.get(
    "",
    description="Endpoint to return a list of job script templates",
    response_model=Page[JobTemplateListView],
)
async def job_script_template_get_list(
    list_params: ListParams = Depends(),
    include_null_identifier: bool = Query(False),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_TEMPLATES_VIEW, commit=False)),
):
    """Get a list of job script templates."""
    logger.debug("Preparing to list job script templates")

    list_kwargs = list_params.dict(exclude_unset=True, exclude={"user_only", "include_parent"})

    if list_params.user_only:
        list_kwargs["owner_email"] = secure_services.identity_payload.email

    return await secure_services.crud.template.paginated_list(
        **list_kwargs,
        include_null_identifier=include_null_identifier,
    )


@router.put(
    "/{id_or_identifier}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script template by id or identifier",
    response_model=JobTemplateDetailedView,
)
async def job_script_template_update(
    update_request: JobTemplateUpdateRequest,
    id_or_identifier: int | str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script template {id_or_identifier=} with {update_request=}")
    await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    return await secure_services.crud.template.update(
        id_or_identifier, **update_request.dict(exclude_unset=True)
    )


@router.delete(
    "/{id_or_identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script template by id or identifier",
)
async def job_script_template_delete(
    id_or_identifier: int | str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script template with {id_or_identifier=}")
    await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    await secure_services.crud.template.delete(id_or_identifier)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id_or_identifier}/upload/template/{file_name:path}",
    description="Endpoint to get a file from a job script template by id or identifier",
)
async def job_script_template_get_file(
    id_or_identifier: int | str = Path(),
    file_name: str = Path(),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_TEMPLATES_VIEW, commit=False)),
):
    """
    Get a job script template file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    logger.debug(f"Getting template file {file_name=} from job script template {id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(id_or_identifier)
    job_script_template_file = await secure_services.file.template.get(job_script_template.id, file_name)
    return StreamingResponse(
        content=await secure_services.file.template.stream_file_content(job_script_template_file),
        media_type="text/plain",
        headers={"filename": job_script_template_file.filename},
    )


@router.put(
    "/{id_or_identifier}/upload/template/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier",
    response_model=TemplateFileDetailedView,
)
async def job_script_template_upload_file(
    id_or_identifier: int | str = Path(),
    file_type: FileType = Path(),
    upload_file: UploadFile = File(..., description="File to upload"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Upload a file to a job script template by id or identifier."""
    if upload_file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The upload file has no filename",
        )

    logger.debug(f"Uploading file {upload_file.filename} to job script template {id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )

    return await secure_services.file.template.upsert(
        parent_id=job_script_template.id,
        filename=upload_file.filename,
        upload_content=upload_file,
        file_type=file_type,
    )


@router.delete(
    "/{id_or_identifier}/upload/template/{file_name:path}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file to a job script template by id or identifier",
)
async def job_script_template_delete_file(
    id_or_identifier: int | str = Path(),
    file_name: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Delete a file from a job script template by id or identifier."""
    job_script_template = await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    job_script_template_file = await secure_services.file.template.get(job_script_template.id, file_name)
    await secure_services.file.template.delete(job_script_template_file)


@router.get(
    "/{id_or_identifier}/upload/workflow",
    description="Endpoint to get a workflow file from a job script template by id or identifier",
)
async def job_script_workflow_get_file(
    id_or_identifier: int | str = Path(),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_TEMPLATES_VIEW, commit=False)),
):
    """
    Get a workflow file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    logger.debug(f"Getting workflow file from job script template {id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(id_or_identifier)
    workflow_file = await secure_services.file.workflow.get(job_script_template.id, WORKFLOW_FILE_NAME)
    return StreamingResponse(
        content=await secure_services.file.workflow.stream_file_content(workflow_file),
        media_type="text/plain",
        headers={"filename": WORKFLOW_FILE_NAME},
    )


@router.put(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier",
    response_model=WorkflowFileDetailedView,
)
async def job_script_workflow_upload_file(
    id_or_identifier: int | str = Path(),
    runtime_config: RunTimeConfig
    | None = Body(
        None, description="Runtime configuration is optional when the workflow file already exists"
    ),
    upload_file: UploadFile = File(..., description="File to upload"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Upload a file to a job script workflow by id or identifier."""
    logger.debug(f"Uploading workflow file to job script template {id_or_identifier=}: {runtime_config}")
    job_script_template = await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )

    upsert_kwargs = dict(
        parent_id=job_script_template.id, filename=WORKFLOW_FILE_NAME, upload_content=upload_file
    )

    try:
        await secure_services.file.workflow.get(job_script_template.id, WORKFLOW_FILE_NAME)
        file_exist = True
    except ServiceError:
        file_exist = False

    if runtime_config is None and file_exist is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Runtime configuration is required when the workflow file does not exist",
        )
    elif runtime_config is not None:
        upsert_kwargs["runtime_config"] = runtime_config.dict()

    return await secure_services.file.workflow.upsert(**upsert_kwargs)


@router.delete(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a workflow file from a job script template by id or identifier",
)
async def job_script_workflow_delete_file(
    id_or_identifier: int | str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_TEMPLATES_EDIT, ensure_email=True)
    ),
):
    """Delete a workflow file from a job script template by id or identifier."""
    logger.debug(f"Deleting workflow file from job script template {id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(
        id_or_identifier, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    workflow_file = await secure_services.file.workflow.get(job_script_template.id, WORKFLOW_FILE_NAME)
    await secure_services.file.workflow.delete(workflow_file)


@router.delete(
    "/upload/garbage-collector",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint to delete all unused files from the job script template file storage",
    tags=["Garbage collector"],
)
async def job_script_template_garbage_collector(
    background_tasks: BackgroundTasks,
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_TEMPLATES_EDIT)),
):
    """Delete all unused files from jobbergate templates on the file storage."""
    logger.info("Starting garbage collection from jobbergate file storage")
    background_tasks.add_task(
        garbage_collect,
        secure_services.session,
        secure_services.bucket,
        [JobScriptTemplateFile, WorkflowFile],
        background_tasks,
    )
    return {"description": "Garbage collection started"}
