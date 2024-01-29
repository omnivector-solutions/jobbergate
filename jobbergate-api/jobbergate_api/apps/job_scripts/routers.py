"""Router for the Job Script Template resource."""
from typing import cast

from buzz import handle_errors
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from loguru import logger

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.garbage_collector import garbage_collect
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScriptFile
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCloneRequest,
    JobScriptCreateRequest,
    JobScriptDetailedView,
    JobScriptListView,
    JobScriptUpdateRequest,
    RenderFromTemplateRequest,
)
from jobbergate_api.apps.job_scripts.tools import inject_sbatch_params
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.schemas import ListParams
from jobbergate_api.apps.services import ServiceError

router = APIRouter(prefix="/job-scripts", tags=["Job Scripts"])


@router.delete(
    "/clean-unused-entries",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint to automatically clean unused job scripts depending on a threshold",
    tags=["Garbage collector"],
)
def job_script_auto_clean_unused_entries(
    background_tasks: BackgroundTasks,
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Automatically clean unused job scripts depending on a threshold."""
    logger.info("Starting automatically cleanup for unused job scripts")
    background_tasks.add_task(secure_services.crud.job_script.auto_clean_unused_job_scripts)
    return {"description": "Automatically cleanup started"}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptDetailedView,
    description="Endpoint for creating a stand alone job script. Use file upload to add files.",
)
async def job_script_create(
    create_request: JobScriptCreateRequest,
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a stand alone job script."""
    logger.info(f"Creating a new job script with {create_request=}")

    if secure_services.identity_payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    return await secure_services.crud.job_script.create(
        owner_email=secure_services.identity_payload.email,
        **create_request.dict(exclude_unset=True),
    )


@router.post(
    "/clone/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptDetailedView,
    description="Endpoint for cloning a job script to a new entry owned by the user",
)
async def job_script_clone(
    id: int = Path(),
    clone_request: JobScriptCloneRequest | None = None,
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Clone a job script by its id."""
    logger.info(f"Cloning a job script from {id=} with {clone_request=}")

    if clone_request is None:
        clone_request = JobScriptCloneRequest()

    original_instance = await secure_services.crud.job_script.get(id, include_files=True)
    cloned_instance = await secure_services.crud.job_script.clone_instance(
        original_instance,
        owner_email=secure_services.identity_payload.email,
        **clone_request.dict(exclude_unset=True, exclude_none=True),
    )

    for file in original_instance.files:
        await secure_services.file.job_script.clone_instance(file, cloned_instance.id)

    # Get again to update the file data
    return await secure_services.crud.job_script.get(cloned_instance.id, include_files=True)


@router.post(
    "/render-from-template/{id_or_identifier}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptDetailedView,
    description="Endpoint for job script creation",
)
async def job_script_create_from_template(
    create_request: JobScriptCreateRequest,
    render_request: RenderFromTemplateRequest,
    id_or_identifier: int | str = Path(...),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Create a new job script from a job script template."""
    logger.info(f"Creating a new job script from {id_or_identifier=} with {create_request=}")

    base_template = cast(
        JobScriptTemplate, await secure_services.crud.template.get(id_or_identifier, include_files=True)
    )

    required_map = render_request.template_output_name_mapping

    required_keys = set(required_map.keys())
    provided_keys = set(f.filename for f in base_template.template_files)
    missing_keys = required_keys - provided_keys
    if len(missing_keys) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The following required files are missing for job template {}: {}".format(
                id_or_identifier, ", ".join(missing_keys)
            ),
        )

    mapped_template_files = {
        new_filename: file
        for file in base_template.template_files
        if (new_filename := required_map.get(file.filename, None))
    }

    entrypoint_files = [f for f in mapped_template_files.values() if f.file_type == FileType.ENTRYPOINT]
    if len(entrypoint_files) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exactly one entrypoint file must be specified, got {len(entrypoint_files)}",
        )

    job_script = await secure_services.crud.job_script.create(
        owner_email=secure_services.identity_payload.email,
        parent_template_id=base_template.id,
        **create_request.dict(exclude_unset=True),
    )

    for new_filename, template_file in mapped_template_files.items():
        file_content = await secure_services.file.template.render(
            template_file,
            render_request.param_dict,
        )

        if template_file.file_type == FileType.ENTRYPOINT and render_request.sbatch_params:
            with handle_errors(
                "Failed to inject sbatch params into the entrypoint file",
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
            ):
                file_content = inject_sbatch_params(file_content, render_request.sbatch_params)

        await secure_services.file.job_script.upsert(
            parent_id=job_script.id,
            filename=new_filename,
            upload_content=file_content,
            file_type=template_file.file_type,
        )

    return await secure_services.crud.job_script.get(job_script.id, include_files=True)


@router.get(
    "/{id}",
    description="Endpoint to return a job script by its id",
    response_model=JobScriptDetailedView,
)
async def job_script_get(
    id: int = Path(),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_VIEW, commit=False)),
):
    """Get a job script by id."""
    logger.info(f"Getting job script {id=}")
    return await secure_services.crud.job_script.get(id, include_files=True)


@router.get(
    "",
    description="Endpoint to return a list of job scripts",
    response_model=Page[JobScriptListView],
)
async def job_script_get_list(
    list_params: ListParams = Depends(),
    from_job_script_template_id: int
    | None = Query(
        None,
        description="Filter job-scripts by the job-script-template-id they were created from.",
    ),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_VIEW, commit=False)),
):
    """Get a list of job scripts."""
    logger.debug("Preparing to list job scripts")

    list_kwargs = list_params.dict(exclude_unset=True, exclude={"user_only"})

    if from_job_script_template_id is not None:
        list_kwargs["parent_template_id"] = from_job_script_template_id
    if list_params.user_only:
        list_kwargs["owner_email"] = secure_services.identity_payload.email

    return await secure_services.crud.job_script.paginated_list(**list_kwargs)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job script by id",
    response_model=JobScriptListView,
)
async def job_script_update(
    update_params: JobScriptUpdateRequest,
    id: int = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Update a job script template by id or identifier."""
    logger.info(f"Updating job script {id=} with {update_params=}")
    await secure_services.crud.job_script.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    return await secure_services.crud.job_script.update(id, **update_params.dict(exclude_unset=True))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete a job script by id",
)
async def job_script_delete(
    id: int = Path(...),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Delete a job script template by id or identifier."""
    logger.info(f"Deleting job script {id=}")
    await secure_services.crud.job_script.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    await secure_services.crud.job_script.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{id}/upload/{file_name:path}",
    description="Endpoint to get a file from a job script",
)
async def job_script_get_file(
    id: int = Path(...),
    file_name: str = Path(...),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_VIEW, commit=False)),
):
    """
    Get a job script file.

    Note:
        See https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
    """
    job_script = await secure_services.crud.job_script.get(id)
    job_script_file = await secure_services.file.job_script.get(job_script.id, file_name)
    return StreamingResponse(
        content=await secure_services.file.job_script.stream_file_content(job_script_file),
        media_type="text/plain",
        headers={"filename": job_script_file.filename},
    )


@router.put(
    "/{id}/upload/{file_type}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a file to a job script file",
)
async def job_script_upload_file(
    id: int = Path(...),
    file_type: FileType = Path(...),
    upload_file: UploadFile = File(..., description="File to upload"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Upload a file to a job script."""
    if upload_file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The upload file has no filename",
        )

    logger.debug(f"Uploading file {upload_file.filename} to job script {id=}")

    job_script = await secure_services.crud.job_script.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )

    await secure_services.file.job_script.upsert(
        parent_id=job_script.id,
        filename=upload_file.filename,
        upload_content=upload_file,
        file_type=file_type,
    )


@router.delete(
    "/{id}/upload/{file_name}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to delete a file from a job script",
)
async def job_script_delete_file(
    id: int = Path(...),
    file_name: str = Path(...),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SCRIPTS_EDIT, ensure_email=True)
    ),
):
    """Delete a file from a job script template by id or identifier."""
    job_script = await secure_services.crud.job_script.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    job_script_file = await secure_services.file.job_script.get(job_script.id, file_name)
    await secure_services.file.job_script.delete(job_script_file)


@router.delete(
    "/upload/garbage-collector",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint to delete all unused files from the job script file storage",
    tags=["Garbage collector"],
)
def job_script_garbage_collector(
    background_tasks: BackgroundTasks,
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Delete all unused files from job scripts on the file storage."""
    logger.info("Starting garbage collection from jobbergate file storage")
    background_tasks.add_task(
        garbage_collect,
        secure_services.session,
        secure_services.bucket,
        [JobScriptFile],
        background_tasks,
    )
    return {"description": "Garbage collection started"}
