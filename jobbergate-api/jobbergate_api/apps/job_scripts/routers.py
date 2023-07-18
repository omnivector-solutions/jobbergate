"""Router for the JobScript resource."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query
from fastapi import Response as FastAPIResponse
from fastapi import UploadFile, status
from fastapi.responses import PlainTextResponse
from loguru import logger
from sqlalchemy import not_, select
from sqlalchemy.sql import func

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.apps.job_scripts.job_script_files import (
    JOBSCRIPTS_MAIN_FILE_FOLDER,
    JobScriptCreationError,
    JobScriptFiles,
)
from jobbergate_api.apps.job_scripts.models import job_scripts_table, searchable_fields, sortable_fields
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptResponse,
    JobScriptUpdateRequest,
)
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.permissions import Permissions, check_owner
from jobbergate_api.config import settings
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    SecureSession,
    fetch_instance,
    insert_instance,
    render_sql,
    search_clause,
    secure_session,
    sort_clause,
)

router = APIRouter()


async def _fetch_job_script_by_id(
    secure_session: SecureSession,
    job_script_id: int,
) -> JobScriptResponse:
    """
    Fetch a job_script from the database by its id.
    """
    return await fetch_instance(secure_session.session, job_script_id, job_scripts_table, JobScriptResponse)


def _get_override_bucket_name(secure_session: SecureSession) -> Optional[str]:
    """
    Get the override_bucket_name based on organization_id if multi-tenancy is enabled.
    """
    if settings.MULTI_TENANCY_ENABLED:
        return secure_session.identity_payload.organization_id
    return None


@router.post(
    "/job-scripts",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job_script creation",
)
async def job_script_create(
    job_script: JobScriptCreateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
):
    """
    Create a new job script.

    Make a post request to this endpoint with the required values to create a new job script.
    """
    logger.debug(f"Creating {job_script=}")

    jobscript_files = None
    application_name = None
    if job_script.application_id is not None:
        select_query = applications_table.select().where(applications_table.c.id == job_script.application_id)
        logger.trace(f"select_query = {render_sql(secure_session.session, select_query)}")

        raw_result = await secure_session.session.execute(select_query)
        application_data = raw_result.one_or_none()

        if not application_data:
            message = f"Application with id={job_script.application_id} not found."
            logger.warning(message)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

        application = ApplicationResponse.from_orm(application_data)
        application_name = application.application_name

        if application.application_uploaded is False:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Application with id={job_script.application_id} was not uploaded.",
            )
        try:
            jobscript_files = JobScriptFiles.render_from_application(
                application_files=ApplicationFiles.get_from_s3(
                    application.id, override_bucket_name=_get_override_bucket_name(secure_session)
                ),
                user_supplied_parameters=job_script.param_dict or {},
                sbatch_params=job_script.sbatch_params or [],
            )
        except JobScriptCreationError as e:
            message = str(e)
            logger.error(message)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    create_dict = dict(
        **{
            k: v
            for (k, v) in job_script.dict(exclude_unset=True).items()
            if k not in ("param_dict", "sbatch_params")
        },
        job_script_owner_email=secure_session.identity_payload.email,
    )

    logger.debug("Inserting job_script")

    try:
        new_job_script = await insert_instance(
            secure_session.session,
            job_scripts_table,
            create_dict,
            JobScriptResponse,
            trace_query=True,
        )

        if jobscript_files:
            jobscript_files.write_to_s3(
                new_job_script.id,
                override_bucket_name=_get_override_bucket_name(secure_session),
            )

    except INTEGRITY_CHECK_EXCEPTIONS as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    except KeyError as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    logger.debug(f"Job-script created: {new_job_script}")

    new_job_script.application_name = application_name
    new_job_script.job_script_files = jobscript_files
    return new_job_script


@router.get(
    "/job-scripts/{job_script_id}",
    description="Endpoint to get a job_script",
    response_model=JobScriptResponse,
)
async def job_script_get(
    job_script_id: int = Query(...),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_VIEW)),
):
    """
    Return the job_script given its id.
    """
    logger.debug(f"Getting {job_script_id=}")

    query = (
        select(job_scripts_table.c, applications_table.c.application_name)
        .where(job_scripts_table.c.id == job_script_id)
        .join(
            applications_table,
            applications_table.columns.id == job_scripts_table.columns.application_id,
            isouter=True,
        )
    )
    logger.debug(f"get_query = {render_sql(secure_session.session, query)}")
    raw_result = await secure_session.session.execute(query)
    job_script_data = raw_result.one_or_none()

    if not job_script_data:
        message = f"JobScript with id={job_script_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    job_script = JobScriptResponse.from_orm(job_script_data)

    try:
        job_script.job_script_files = JobScriptFiles.get_from_s3(
            job_script_id,
            override_bucket_name=_get_override_bucket_name(secure_session),
        )
    except (KeyError, ValueError):
        message = f"JobScript file not found for id={job_script_id}."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.debug(f"Job-script data: {job_script}")

    return job_script


@router.post(
    "/job-scripts/{job_script_id}/upload",
    status_code=status.HTTP_200_OK,
    description="Endpoint to upload a new job script file.",
)
async def job_script_create_file_content(
    job_script_id: int = Query(...),
    job_script_file: UploadFile = File(...),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Create a job script file (only if the job script has none)."""
    logger.debug(f"Creating the main file for {job_script_id=}")

    job_script = await _fetch_job_script_by_id(secure_session, job_script_id)
    check_owner(
        job_script.job_script_owner_email, secure_session.identity_payload.email, job_script_id, "job_script"
    )

    jobscript_files = JobScriptFiles.get_from_single_upload_file(job_script_file)
    jobscript_files.write_to_s3(
        job_script_id,
        remove_previous_files=True,
        override_bucket_name=_get_override_bucket_name(secure_session),
    )

    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.id == job_script_id)
        .values(updated_at=func.now())
    )
    await secure_session.session.execute(update_query)
    logger.debug(f"Success creating job script files from single upload file for {job_script_id=}")
    return dict(message=f"Successfully uploaded {job_script_file.filename} for {job_script_id=}")


@router.patch(
    "/job-scripts/{job_script_id}/upload",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to replace a job script file.",
)
async def job_script_replace_file_content(
    job_script_id: int = Query(...),
    job_script_file: UploadFile = File(...),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
):
    """Replace the content on a job script file."""
    logger.debug(f"Replacing the main file from {job_script_id=}")

    job_script = await _fetch_job_script_by_id(secure_session, job_script_id)
    check_owner(
        job_script.job_script_owner_email, secure_session.identity_payload.email, job_script_id, "job_script"
    )

    file_manager = JobScriptFiles.file_manager_factory(
        job_script_id, override_bucket_name=_get_override_bucket_name(secure_session)
    )
    file_content = job_script_file.file.read().decode("utf-8")

    for s3_path in file_manager.keys():
        root_dir = s3_path.parts[0]
        if root_dir == JOBSCRIPTS_MAIN_FILE_FOLDER:
            file_manager[s3_path] = file_content
            update_query = (
                job_scripts_table.update()
                .where(job_scripts_table.c.id == job_script_id)
                .values(updated_at=func.now())
            )
            await secure_session.session.execute(update_query)
            logger.debug(f"Success replacing the main file from {job_script_id=}")
            return None

    message = f"Main file from {job_script_id=} was not found."
    logger.warning(message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


@router.get(
    "/job-scripts/{job_script_id}/download",
    status_code=status.HTTP_200_OK,
    description="Endpoint to download a job script file.",
)
async def job_script_download_file(
    job_script_id: int = Query(...),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_VIEW)),
):
    """Download the job script file."""
    logger.debug(f"Downloading main file from {job_script_id=}")

    await _fetch_job_script_by_id(secure_session, job_script_id)

    file_manager = JobScriptFiles.file_manager_factory(
        job_script_id, override_bucket_name=_get_override_bucket_name(secure_session)
    )

    for s3_path in file_manager.keys():
        root_dir = s3_path.parts[0]
        if root_dir == JOBSCRIPTS_MAIN_FILE_FOLDER:
            file_content = file_manager[s3_path]
            filename = s3_path.relative_to(JOBSCRIPTS_MAIN_FILE_FOLDER).as_posix()
            return PlainTextResponse(file_content, media_type="text/plain", headers={"filename": filename})

    message = f"Main file from {job_script_id=} was not found."
    logger.warning(message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


@router.get(
    "/job-scripts",
    description="Endpoint to list job_scripts",
    responses=ok_response(JobScriptResponse),
)
async def job_script_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(False),
    include_archived: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    from_application_id: Optional[int] = Query(
        None,
        description="Filter job-scripts by the application-id they were created from.",
    ),
    sort_ascending: bool = Query(True),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_VIEW)),
):
    """
    List job_scripts for the authenticated user.

    Note::

       Use responses instead of response_model to skip a second round of validation and serialization. This
       is already happening in the ``package_response`` method. So, we uses ``responses`` so that FastAPI
       can generate the correct OpenAPI spec but not post-process the response.
    """
    logger.debug("Preparing to list job-scripts")

    query = select(job_scripts_table.c, applications_table.c.application_name)

    if not all:
        query = query.where(
            job_scripts_table.c.job_script_owner_email == secure_session.identity_payload.email
        )
    if not include_archived:
        query = query.where(not_(job_scripts_table.c.is_archived))
    if from_application_id is not None:
        query = query.where(job_scripts_table.c.application_id == from_application_id)
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))
    else:
        query = query.order_by(job_scripts_table.c.id.asc())

    full_query = query.join(
        applications_table,
        applications_table.columns.id == job_scripts_table.columns.application_id,
        isouter=True,
    )

    logger.debug(f"Query = {render_sql(secure_session.session, full_query)}")
    return await package_response(secure_session.session, JobScriptResponse, full_query, pagination)


@router.delete(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job script",
)
async def job_script_delete(
    job_script_id: int = Query(..., description="id of the job script to delete"),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
):
    """
    Delete job_script given its id.
    """
    job_script = await _fetch_job_script_by_id(secure_session, job_script_id)
    check_owner(
        job_script.job_script_owner_email, secure_session.identity_payload.email, job_script_id, "job_script"
    )

    logger.debug(f"Orphaning job_submissions submitted from job_script {job_script_id=}")
    update_query = (
        job_submissions_table.update()
        .where(job_submissions_table.c.job_script_id == job_script_id)
        .values(dict(job_script_id=None))
    )
    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")
    await secure_session.session.execute(update_query)

    logger.debug(f"Preparing to delete {job_script_id=}")
    delete_query = job_scripts_table.delete().where(job_scripts_table.c.id == job_script_id)
    logger.trace(f"delete_query = {render_sql(secure_session.session, delete_query)}")
    await secure_session.session.execute(delete_query)

    try:
        JobScriptFiles.delete_from_s3(
            job_script_id,
            override_bucket_name=_get_override_bucket_name(secure_session),
        )
    except KeyError:
        # There is no need to raise an error if we try to delete a file that does not exist
        logger.warning(f"Tried to delete {job_script_id=}, but it was not found on S3.")

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_script given the id",
    response_model=JobScriptResponse,
)
async def job_script_update(
    job_script_id: int,
    job_script: JobScriptUpdateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SCRIPTS_EDIT)),
):
    """
    Update a job_script given its id.
    """
    logger.debug(f"Updating {job_script_id=}")
    old_job_script = await _fetch_job_script_by_id(secure_session, job_script_id)
    check_owner(
        old_job_script.job_script_owner_email,
        secure_session.identity_payload.email,
        job_script_id,
        "job_script",
    )

    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.id == job_script_id)
        .values(
            job_script.dict(exclude_unset=True, exclude={"job_script_files"}),
        )
        .returning(job_scripts_table)
    )
    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")

    try:
        raw_result = await secure_session.session.execute(update_query)
    except INTEGRITY_CHECK_EXCEPTIONS as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    job_script_data = raw_result.one_or_none()

    if job_script_data is None:
        message = f"JobScript with id={job_script_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    job_script_response = JobScriptResponse.from_orm(job_script_data)

    try:
        if job_script.job_script_files:
            job_script.job_script_files.write_to_s3(job_script_id)
            job_script_response.job_script_files = job_script.job_script_files
        else:
            job_script_response.job_script_files = JobScriptFiles.get_from_s3(
                job_script_id,
                override_bucket_name=_get_override_bucket_name(secure_session),
            )
    except (KeyError, ValueError) as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for JobScript with id={job_script_id} not found in S3.",
        )

    return job_script_response


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
