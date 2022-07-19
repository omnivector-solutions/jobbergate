"""
Router for the JobScript resource.
"""
import json
import tarfile
import tempfile
from io import StringIO
from typing import List, Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Query, status
from jinja2 import Template
from loguru import logger
from yaml import safe_load

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.apps.job_scripts.models import job_scripts_table, searchable_fields, sortable_fields
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptPartialResponse,
    JobScriptResponse,
    JobScriptUpdateRequest,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.s3_manager import get_s3_object_as_tarfile, s3man_applications, s3man_jobscripts
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    database,
    render_sql,
    search_clause,
    sort_clause,
)

router = APIRouter()


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    logger.debug("Preparing to inject sbatch params into job script")

    if not sbatch_params:
        logger.warning("Sbatch param list is empty")
        return job_script_data_as_string

    first_sbatch_index = job_script_data_as_string.find("#SBATCH")
    string_slice = job_script_data_as_string[first_sbatch_index:]
    line_end = string_slice.find("\n") + first_sbatch_index + 1

    inner_string = ""
    for parameter in sbatch_params:
        inner_string += "#SBATCH " + parameter + "\\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:line_end] + inner_string + job_script_data_as_string[line_end:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


def render_template(template_files, param_dict_flat):
    """
    Render the templates as strings using jinja2.
    """
    logger.debug("Rendering the templates as strings using jinja2")
    for key, value in template_files.items():
        template = Template(value)
        rendered_js = template.render(data=param_dict_flat)
        template_files[key] = rendered_js
    job_script_data_as_string = json.dumps(template_files)
    return job_script_data_as_string


def build_job_script_data_as_string(s3_application_tar, param_dict):
    """
    Return the job_script_data_as_string from the S3 application and the templates.
    """
    logger.debug("Building the job script file from the S3 application and the templates")

    support_files_output = param_dict["jobbergate_config"].get("supporting_files_output_name")
    if support_files_output is None:
        support_files_output = dict()

    supporting_files = param_dict["jobbergate_config"].get("supporting_files")
    if supporting_files is None:
        supporting_files = list()

    default_template = [
        default_template := param_dict["jobbergate_config"].get("default_template"),
        "templates/" + default_template,
    ]

    template_files = {}
    for member in s3_application_tar.getmembers():
        if member.name in default_template:
            contentfobj = s3_application_tar.extractfile(member)
            template_files["application.sh"] = contentfobj.read().decode("utf-8")
        if member.name in supporting_files:
            match = [x for x in support_files_output if member.name in x]
            contentfobj = s3_application_tar.extractfile(member)
            filename = support_files_output[match[0]][0]
            template_files[filename] = contentfobj.read().decode("utf-8")

    # Use tempfile to generate .tar in memory - NOT write to disk
    param_dict_flat = {}
    for (key, value) in param_dict.items():
        if isinstance(value, dict):
            for nest_key, nest_value in value.items():
                param_dict_flat[nest_key] = nest_value
        else:
            param_dict_flat[key] = value
    with tempfile.NamedTemporaryFile("wb", suffix=".tar.gz", delete=False) as f:
        with tarfile.open(fileobj=f, mode="w:gz") as rendered_tar:
            for member in s3_application_tar.getmembers():
                if member.name in supporting_files:
                    contentfobj = s3_application_tar.extractfile(member)
                    supporting_file = contentfobj.read().decode("utf-8")
                    template = Template(supporting_file)
                    rendered_str = template.render(data=param_dict_flat)
                    tarinfo = tarfile.TarInfo(member.name)
                    rendered_tar.addfile(tarinfo, StringIO(rendered_str))
        f.flush()
        f.seek(0)

    job_script_data_as_string = render_template(template_files, param_dict_flat)

    logger.debug("Done building the job script file")
    return job_script_data_as_string


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

    logger.debug("Fetching application tarfile")
    s3_application_tar = get_s3_object_as_tarfile(s3man_applications, application.id)

    identity_claims = IdentityClaims.from_token_payload(token_payload)

    create_dict = dict(
        **{k: v for (k, v) in job_script.dict(exclude_unset=True).items() if k != "param_dict"},
        job_script_owner_email=identity_claims.email,
    )

    # Use application_config from the application as a baseline of defaults
    logger.debug(f"APP CONFIG: {application.application_config}")
    param_dict = safe_load(application.application_config)

    # User supplied param dict is optional and may override defaults
    param_dict.update(**job_script.param_dict)

    job_script_data_as_string = build_job_script_data_as_string(s3_application_tar, param_dict)

    sbatch_params = create_dict.pop("sbatch_params", [])
    job_script_data_as_string = inject_sbatch_params(job_script_data_as_string, sbatch_params)

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

            s3man_jobscripts[job_script_data["id"]] = job_script_data_as_string

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            logger.error(f"Reverting database transaction: {str(e)}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        except KeyError as e:
            logger.error(f"Reverting database transaction: {str(e)}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    logger.debug(f"Job-script created: {job_script_data}")
    job_script_response = dict(
        **job_script_data,
        job_script_data_as_string=job_script_data_as_string,
    )
    return job_script_response


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

    job_script_response = dict(job_script)

    try:
        job_script_response["job_script_data_as_string"] = s3man_jobscripts[job_script_id]
    except KeyError:
        message = f"JobScript file not found for id={job_script_id}."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.debug(f"Job-script data: {job_script_response=}")

    return job_script_response


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
        del s3man_jobscripts[job_script_id]
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
            job_script.dict(exclude_unset=True, exclude={"job_script_data_as_string"}),
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
            if job_script.job_script_data_as_string:
                s3man_jobscripts[job_script_id] = job_script.job_script_data_as_string
                job_script_response["job_script_data_as_string"] = job_script.job_script_data_as_string
            else:
                job_script_response["job_script_data_as_string"] = s3man_jobscripts[job_script_id]
        except KeyError as e:
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
