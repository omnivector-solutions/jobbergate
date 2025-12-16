"""Router for the Job Script Template resource."""

import snick
from buzz import require_condition
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi import Response as FastAPIResponse
from fastapi_pagination import Page
from loguru import logger
from pydantic import AnyUrl
from sqlalchemy.exc import IntegrityError

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateBaseDetailedView,
    JobTemplateCloneRequest,
    JobTemplateCreateRequest,
    JobTemplateDetailedView,
    JobTemplateListView,
    JobTemplateUpdateRequest,
    RunTimeConfig,
    TemplateFileDetailedView,
    WorkflowFileDetailedView,
)
from jobbergate_api.apps.job_script_templates.tools import coerce_id_or_identifier
from jobbergate_api.apps.permissions import Permissions, can_bypass_ownership_check
from jobbergate_api.apps.schemas import ListParams
from jobbergate_api.apps.services import ServiceError

router = APIRouter(prefix="/job-script-templates", tags=["Job Script Templates"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateBaseDetailedView,
    description="Endpoint for job script template creation",
)
async def job_script_template_create(
    create_request: JobTemplateCreateRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Create a new job script template."""
    logger.info(f"Creating a new job script template with {create_request=}")

    try:
        return await secure_services.crud.template.create(
            owner_email=secure_services.identity_payload.email,
            **create_request.model_dump(exclude_unset=True),
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
    id_or_identifier: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_READ, commit=False)
    ),
):
    """Get a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.info(f"Getting job script template with {typed_id_or_identifier=}")
    return await secure_services.crud.template.get(typed_id_or_identifier, include_files=True)


@router.post(
    "/clone/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobTemplateDetailedView,
    description="Endpoint for cloning a job script template to a new entry owned by the user",
)
async def job_script_template_clone(
    id_or_identifier: str = Path(),
    clone_request: JobTemplateCloneRequest | None = None,
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Clone a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.info(f"Cloning a job script template from {typed_id_or_identifier=} with {clone_request=}")

    if clone_request is None:
        clone_request = JobTemplateCloneRequest()

    original_instance = await secure_services.crud.template.get(typed_id_or_identifier, include_files=True)

    # Identifier is specifically set to None to avoid conflicts with the original instance
    new_data = {"identifier": None, **clone_request.model_dump(exclude_unset=True)}
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
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_READ, commit=False)
    ),
):
    """Get a list of job script templates."""
    logger.debug("Preparing to list job script templates")

    list_kwargs = list_params.model_dump(exclude_unset=True, exclude={"user_only", "include_parent"})

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
    response_model=JobTemplateBaseDetailedView,
)
async def job_script_template_update(
    update_request: JobTemplateUpdateRequest,
    id_or_identifier: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_UPDATE, ensure_email=True)
    ),
):
    """Update a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.info(f"Updating job script template {typed_id_or_identifier=} with {update_request=}")
    instance = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            instance, owner_email=secure_services.identity_payload.email
        )
    return await secure_services.crud.template.update(
        typed_id_or_identifier, **update_request.model_dump(exclude_unset=True)
    )


@router.delete(
    "/{id_or_identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script template by id or identifier",
)
async def job_script_template_delete(
    id_or_identifier: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_DELETE, ensure_email=True)
    ),
):
    """Delete a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.info(f"Deleting job script template with {typed_id_or_identifier=}")
    isinstance = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            isinstance, owner_email=secure_services.identity_payload.email
        )
    await secure_services.crud.template.delete(typed_id_or_identifier)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id_or_identifier}/upload/template/{file_name:path}",
    description="Endpoint to get a file from a job script template by id or identifier",
)
async def job_script_template_get_file(
    id_or_identifier: str = Path(),
    file_name: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_READ, commit=False)
    ),
):
    """
    Get a job script template file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.debug(f"Getting template file {file_name=} from job script template {typed_id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    job_script_template_file = await secure_services.file.template.get(job_script_template.id, file_name)
    return FastAPIResponse(
        content=await secure_services.file.template.get_file_content(job_script_template_file),
        media_type="text/plain",
        headers={"filename": job_script_template_file.filename},
    )


async def _upsert_template_file(
    id_or_identifier: str,
    file_type: FileType,
    filename: str,
    upload_content: str | bytes | AnyUrl | UploadFile | None,
    previous_filename: str | None,
    secure_services: SecureService,
):
    """
    Provide an auxillary function to be used for uploading from file object or URL.
    """
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            job_script_template, owner_email=secure_services.identity_payload.email
        )

    return await secure_services.file.template.upsert(
        parent_id=job_script_template.id,
        filename=filename,
        upload_content=upload_content,
        previous_filename=previous_filename,
        file_type=file_type,
    )


@router.put(
    "/{id_or_identifier}/upload/template/{file_type}",
    status_code=status.HTTP_200_OK,
    description=(
        "Endpoint to upload a file to a job script template by id or identifier. "
        "If a previous filename is provided, the file will be renamed from that. "
        "Upload file is optional in this scenario since the file content can be copied from previous file."
    ),
    response_model=TemplateFileDetailedView,
)
async def job_script_template_upload_file(
    id_or_identifier: str = Path(),
    file_type: FileType = Path(),
    filename: str | None = Query(None, max_length=255),
    upload_file: UploadFile | None = File(None, description="File to upload"),
    previous_filename: str | None = Query(
        None, description="Previous name of the file in case a rename is needed", max_length=255
    ),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Upload a file to a job script template by id or identifier."""
    # This is included for backwards compatibility with the previous implementation
    # where filename was recovered from the upload_file object
    filename = filename or getattr(upload_file, "filename")
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be provided either as a query parameter or as part of the file upload",
        )

    logger.debug(
        f"Uploading {filename=} to job template {id_or_identifier=}; {file_type=}; {previous_filename=}"
    )
    return await _upsert_template_file(
        id_or_identifier,
        file_type,
        filename,
        upload_file,
        previous_filename,
        secure_services,
    )


@router.put(
    "/{id_or_identifier}/upload-by-url/template/{file_type}",
    status_code=status.HTTP_200_OK,
    description=(
        "Endpoint to upload a file to a job script template by id or identifier using a file URL. "
        "If a previous filename is provided, the file will be renamed from that. "
    ),
    response_model=TemplateFileDetailedView,
)
async def job_script_template_upload_file_by_url(
    id_or_identifier: str = Path(),
    file_type: FileType = Path(),
    filename: str | None = Query(None, max_length=255),
    file_url: AnyUrl = Query(..., description="URL of the file to upload"),
    previous_filename: str | None = Query(
        None, description="Previous name of the file in case a rename is needed", max_length=255
    ),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Upload a file to a job script template by id or identifier using file URL."""

    if filename is None:
        url_path = file_url.path or ""
        (*_, filename) = url_path.split("/")
        require_condition(
            filename != "",
            f"Filename could not be extracted from the provided URL: {file_url}",
            raise_exc_class=HTTPException,
            exc_builder=lambda params: params.raise_exc_class(
                status_code=status.HTTP_400_BAD_REQUEST,  # type: ignore
                detail=params.message,  # type: ignore
            ),
        )

    # This is needed to make static type checkers happy. It shouldn't be able to happen
    assert filename is not None

    logger.debug(
        snick.unwrap(
            f"""
            Uploading file {filename=} from {file_url}
            to job template {id_or_identifier=};
            {file_type=}; {previous_filename=}
            """
        )
    )
    return await _upsert_template_file(
        id_or_identifier,
        file_type,
        filename,
        file_url,
        previous_filename,
        secure_services,
    )


@router.delete(
    "/{id_or_identifier}/upload/template/{file_name:path}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file to a job script template by id or identifier",
)
async def job_script_template_delete_file(
    id_or_identifier: str = Path(),
    file_name: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_DELETE, ensure_email=True)
    ),
):
    """Delete a file from a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            job_script_template, owner_email=secure_services.identity_payload.email
        )
    job_script_template_file = await secure_services.file.template.get(job_script_template.id, file_name)
    await secure_services.file.template.delete(job_script_template_file)


@router.get(
    "/{id_or_identifier}/upload/workflow",
    description="Endpoint to get a workflow file from a job script template by id or identifier",
)
async def job_script_workflow_get_file(
    id_or_identifier: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_READ, commit=False)
    ),
):
    """
    Get a workflow file by id or identifier.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.debug(f"Getting workflow file from job script template {typed_id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    workflow_file = await secure_services.file.workflow.get(job_script_template.id, WORKFLOW_FILE_NAME)
    return FastAPIResponse(
        content=await secure_services.file.workflow.get_file_content(workflow_file),
        media_type="text/plain",
        headers={"filename": WORKFLOW_FILE_NAME},
    )


async def _upsert_workflow_file(
    id_or_identifier: str,
    runtime_config: RunTimeConfig | None,
    upload_content: str | bytes | AnyUrl | UploadFile,
    secure_services: SecureService,
):
    """
    Provide an auxillary function to be used for uploading from file object or URL.
    """
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.debug(
        f"Uploading workflow file to job script template {typed_id_or_identifier=}: {runtime_config}"
    )
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            job_script_template, owner_email=secure_services.identity_payload.email
        )
    upsert_kwargs = dict(
        parent_id=job_script_template.id, filename=WORKFLOW_FILE_NAME, upload_content=upload_content
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
        upsert_kwargs["runtime_config"] = runtime_config.model_dump()

    return await secure_services.file.workflow.upsert(**upsert_kwargs)


@router.put(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier",
    response_model=WorkflowFileDetailedView,
)
async def job_script_workflow_upload_file(
    id_or_identifier: str = Path(),
    runtime_config: RunTimeConfig | None = Body(
        None, description="Runtime configuration is optional when the workflow file already exists"
    ),
    upload_file: UploadFile = File(..., description="File to upload"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Upload a file to a job script workflow by id or identifier."""
    return await _upsert_workflow_file(id_or_identifier, runtime_config, upload_file, secure_services)


@router.put(
    "/{id_or_identifier}/upload-by-url/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script template by id or identifier from a provided URL.",
    response_model=WorkflowFileDetailedView,
)
async def job_script_upload_file_by_url(
    id_or_identifier: str = Path(),
    runtime_config: RunTimeConfig | None = Body(
        None, description="Runtime configuration is optional when the workflow file already exists"
    ),
    file_url: AnyUrl = Query(..., description="URL of the file to upload"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_CREATE, ensure_email=True)
    ),
):
    """Upload a file to a job script workflow by id or identifier from a URL."""
    return await _upsert_workflow_file(id_or_identifier, runtime_config, file_url, secure_services)


@router.delete(
    "/{id_or_identifier}/upload/workflow",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a workflow file from a job script template by id or identifier",
)
async def job_script_workflow_delete_file(
    id_or_identifier: str = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_TEMPLATES_DELETE, ensure_email=True)
    ),
):
    """Delete a workflow file from a job script template by id or identifier."""
    typed_id_or_identifier: int | str = coerce_id_or_identifier(id_or_identifier)
    logger.debug(f"Deleting workflow file from job script template {typed_id_or_identifier=}")
    job_script_template = await secure_services.crud.template.get(typed_id_or_identifier)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.template.ensure_attribute(
            job_script_template, owner_email=secure_services.identity_payload.email
        )
    workflow_file = await secure_services.file.workflow.get(job_script_template.id, WORKFLOW_FILE_NAME)
    await secure_services.file.workflow.delete(workflow_file)
