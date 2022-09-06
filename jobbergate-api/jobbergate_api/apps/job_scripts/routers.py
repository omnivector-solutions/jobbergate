"""
Router for the JobScript resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.apps.job_scripts.job_script_files import JobScriptCreationError, JobScriptFiles
from jobbergate_api.apps.job_scripts.models import job_scripts_table, searchable_fields, sortable_fields
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptPartialResponse,
    JobScriptResponse,
    JobScriptUpdateRequest,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    database,
    render_sql,
    search_clause,
    sort_clause,
)

router = APIRouter()


@router.post(
    "/job-scripts",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job_script creation",
)
async def job_script_create(
    job_script: JobScriptCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT)),
):
    """
    Create a new job script.

    Make a post request to this endpoint with the required values to create a new job script.
    """
    logger.debug(f"Creating {job_script=}")

    select_query = applications_table.select().where(applications_table.c.id == job_script.application_id)
    logger.trace(f"select_query = {render_sql(select_query)}")

    raw_application = await database.fetch_one(select_query)

    if not raw_application:
        message = f"Application with id={job_script.application_id} not found."
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    application = ApplicationResponse.parse_obj(raw_application)

    if application.application_uploaded is False:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Application with id={job_script.application_id} was not uploaded.",
        )

    identity_claims = IdentityClaims.from_token_payload(token_payload)

    create_dict = dict(
        **{k: v for (k, v) in job_script.dict(exclude_unset=True).items() if k != "param_dict"},
        job_script_owner_email=identity_claims.email,
    )

    try:
        jobscript_files = JobScriptFiles.render_from_application(
            application_files=ApplicationFiles.get_from_s3(application.id),
            user_supplied_parameters=job_script.param_dict,
            sbatch_params=create_dict.pop("sbatch_params", []),
        )
    except JobScriptCreationError as e:
        message = str(e)
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    logger.debug("Inserting job_script")

    async with database.transaction():

        try:
            insert_query = job_scripts_table.insert().returning(job_scripts_table)
            logger.trace(f"insert_query = {render_sql(insert_query)}")
            job_script_data = await database.fetch_one(query=insert_query, values=create_dict)

            if job_script_data is None:
                message = "An error occurred when inserting the JobScript at the database."
                logger.error(message)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message,
                )

            jobscript_files.write_to_s3(job_script_data["id"])

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            logger.error(f"Reverting database transaction: {str(e)}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        except KeyError as e:
            logger.error(f"Reverting database transaction: {str(e)}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    logger.debug(f"Job-script created: {dict(job_script_data)}")

    response = JobScriptResponse(
        **job_script_data,
        job_script_files=jobscript_files,
    )
    return response


@router.get(
    "/job-scripts/{job_script_id}",
    description="Endpoint to get a job_script",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW))],
)
async def job_script_get(job_script_id: int = Query(...)):
    """
    Return the job_script given its id.
    """
    logger.debug(f"Getting {job_script_id=}")

    query = job_scripts_table.select().where(job_scripts_table.c.id == job_script_id)
    logger.trace(f"get_query = {render_sql(query)}")
    job_script = await database.fetch_one(query)

    if not job_script:
        message = f"JobScript with id={job_script_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    try:
        response = JobScriptResponse(
            **job_script,
            job_script_files=JobScriptFiles.get_from_s3(job_script_id),
        )
    except (KeyError, ValueError):
        message = f"JobScript file not found for id={job_script_id}."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.debug(f"Job-script data: {response}")

    return response


@router.get(
    "/job-scripts",
    description="Endpoint to list job_scripts",
    responses=ok_response(JobScriptPartialResponse),
)
async def job_script_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(False),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_ascending: bool = Query(True),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SCRIPTS_VIEW)),
):
    """
    List job_scripts for the authenticated user.

    Note::

       Use responses instead of response_model to skip a second round of validation and serialization. This
       is already happening in the ``package_response`` method. So, we uses ``responses`` so that FastAPI
       can generate the correct OpenAPI spec but not post-process the response.
    """
    logger.debug("Preparing to list job-scripts")

    query = job_scripts_table.select()
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if not all:
        query = query.where(job_scripts_table.c.job_script_owner_email == identity_claims.email)
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))

    logger.trace(f"Query = {render_sql(query)}")
    return await package_response(JobScriptPartialResponse, query, pagination)


@router.delete(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job script",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_delete(job_script_id: int = Query(..., description="id of the job script to delete")):
    """
    Delete job_script given its id.
    """
    logger.debug(f"Preparing to delete {job_script_id=}")
    where_stmt = job_scripts_table.c.id == job_script_id

    get_query = job_scripts_table.select().where(where_stmt)
    logger.trace(f"get_query = {render_sql(get_query)}")

    raw_job_script = await database.fetch_one(get_query)
    if not raw_job_script:

        message = f"JobScript with id={job_script_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    delete_query = job_scripts_table.delete().where(where_stmt)
    logger.trace(f"delete_query = {render_sql(delete_query)}")
    await database.execute(delete_query)

    try:
        JobScriptFiles.delete_from_s3(job_script_id)
    except KeyError:
        # There is no need to raise an error if we try to delete a file that does not exist
        logger.warning(f"Tried to delete {job_script_id=}, but it was not found on S3.")


@router.put(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_script given the id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SCRIPTS_EDIT))],
)
async def job_script_update(job_script_id: int, job_script: JobScriptUpdateRequest):
    """
    Update a job_script given its id.
    """
    logger.debug(f"Updating {job_script_id=}")

    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.id == job_script_id)
        .values(
            job_script.dict(exclude_unset=True, exclude={"job_script_files"}),
        )
        .returning(job_scripts_table)
    )
    logger.trace(f"update_query = {render_sql(update_query)}")

    async with database.transaction():

        try:
            result = await database.fetch_one(update_query)
        except INTEGRITY_CHECK_EXCEPTIONS as e:
            logger.error(f"Reverting database transaction: {str(e)}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        if result is None:
            message = f"JobScript with id={job_script_id} not found."
            logger.warning(message)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            )

        job_script_response = dict(result)

        try:
            if job_script.job_script_files:
                job_script.job_script_files.write_to_s3(job_script_id)
                job_script_response["job_script_files"] = job_script.job_script_files
            else:
                job_script_response["job_script_files"] = JobScriptFiles.get_from_s3(job_script_id)
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
