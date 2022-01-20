"""
Router for the JobScript resource.
"""
import json
import tarfile
import tempfile
from io import BytesIO, StringIO
from typing import List, Optional

from armasec import TokenPayload
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from jinja2 import Template

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationResponse
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_scripts.schemas import (
    JobScriptCreateRequest,
    JobScriptResponse,
    JobScriptUpdateRequest,
)
from jobbergate_api.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergate_api.pagination import Pagination, Response, package_response
from jobbergate_api.s3_manager import S3Manager
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import database, handle_fk_error

router = APIRouter()
s3man = S3Manager()


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    if sbatch_params == []:
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
    return new_job_script_data_as_string


def get_s3_object_as_tarfile(application_id):
    """
    Return the tarfile of a S3 object.
    """
    try:
        s3_application_obj = s3man.get(app_id=application_id)
    except BotoCoreError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found in S3",
        )
    s3_application_tar = tarfile.open(fileobj=BytesIO(s3_application_obj["Body"].read()))
    return s3_application_tar


def render_template(template_files, param_dict_flat):
    """
    Render the template as string using jinja2.
    """
    for key, value in template_files.items():
        template = Template(value)
        rendered_js = template.render(data=param_dict_flat)
        template_files[key] = rendered_js
    job_script_data_as_string = json.dumps(template_files)
    return job_script_data_as_string


def build_job_script_data_as_string(s3_application_tar, param_dict):
    """
    Return the job_script_data_as string from the S3 application and the templates.
    """
    try:
        support_files_output = param_dict["jobbergate_config"]["supporting_files_output_name"]
    except KeyError:
        support_files_output = {}
    try:
        supporting_files = param_dict["jobbergate_config"]["supporting_files"]
    except KeyError:
        supporting_files = []

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
    for key in param_dict.keys():
        for nest_key, nest_value in param_dict[key].items():
            param_dict_flat[nest_key] = nest_value
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
    return job_script_data_as_string


@router.post(
    "/job-scripts/",
    status_code=status.HTTP_201_CREATED,
    response_model=JobScriptResponse,
    description="Endpoint for job_script creation",
)
async def job_script_create(
    job_script: JobScriptCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-scripts:create")),
):
    """
    Create a new job script.

    Make a post request to this endpoint with the required values to create a new job script.
    """
    select_query = applications_table.select().where(applications_table.c.id == job_script.application_id)
    raw_application = await database.fetch_one(select_query)

    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={job_script.application_id} not found.",
        )
    application = ApplicationResponse.parse_obj(raw_application)
    s3_application_tar = get_s3_object_as_tarfile(application.id)

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    job_script.job_script_owner_email = identity_claims.user_email

    create_dict = job_script.dict(exclude_unset=True)

    param_dict = json.loads(create_dict.pop("param_dict", "{}"))
    job_script_data_as_string = build_job_script_data_as_string(s3_application_tar, param_dict)

    sbatch_params = create_dict.pop("sbatch_params", [])
    create_dict["job_script_data_as_string"] = inject_sbatch_params(job_script_data_as_string, sbatch_params)

    async with database.transaction():
        try:
            insert_query = job_scripts_table.insert()
            inserted_id = await database.execute(query=insert_query, values=create_dict)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Now fetch the newly inserted row. This is necessary to reflect defaults and db modified columns
        query = job_scripts_table.select().where(job_scripts_table.c.id == inserted_id)
        raw_job_script = await database.fetch_one(query)
        response_job_script = JobScriptResponse.parse_obj(raw_job_script)

    return response_job_script


@router.get(
    "/job-scripts/{job_script_id}",
    description="Endpoint to get a job_script",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown("jobbergate:job-scripts:read"))],
)
async def job_script_get(job_script_id: int = Query(...)):
    """
    Return the job_script given it's id.
    """
    query = job_scripts_table.select().where(job_scripts_table.c.id == job_script_id)
    raw_job_script = await database.fetch_one(query)

    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"JobScript with id={job_script_id} not found.",
        )
    job_script = JobScriptResponse.parse_obj(raw_job_script)
    return job_script


@router.get(
    "/job-scripts/", description="Endpoint to list job_scripts", response_model=Response[JobScriptResponse],
)
async def job_script_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(False),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-scripts:read")),
):
    """
    List job_scripts for the authenticated user.
    """
    query = job_scripts_table.select()
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if not all:
        query = query.where(job_scripts_table.c.job_script_owner_email == identity_claims.user_email)
    return await package_response(JobScriptResponse, query, pagination)


@router.delete(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job script",
    dependencies=[Depends(guard.lockdown("jobbergate:job-scripts:delete"))],
)
async def job_script_delete(job_script_id: int = Query(..., description="id of the job script to delete")):
    """
    Delete job_script given its id.
    """
    where_stmt = job_scripts_table.c.id == job_script_id

    get_query = job_scripts_table.select().where(where_stmt)
    raw_job_script = await database.fetch_one(get_query)
    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"JobScript with id={job_script_id} not found.",
        )

    delete_query = job_scripts_table.delete().where(where_stmt)
    with handle_fk_error():
        await database.execute(delete_query)


@router.put(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to update a job_script given the id",
    response_model=JobScriptResponse,
    dependencies=[Depends(guard.lockdown("jobbergate:job-scripts:update"))],
)
async def job_script_update(
    job_script_id: int, job_script: JobScriptUpdateRequest,
):
    """
    Update a job_script given its id.
    """
    update_query = (
        job_scripts_table.update()
        .where(job_scripts_table.c.id == job_script_id)
        .values(job_script.dict(exclude_unset=True))
    )
    async with database.transaction():
        try:
            result = await database.execute(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"JobScript with id={job_script_id} not found.",
            )

        select_query = job_scripts_table.select().where(job_scripts_table.c.id == job_script_id)
        raw_job_script = await database.fetch_one(select_query)
        response_job_script = JobScriptResponse.parse_obj(raw_job_script)

    return response_job_script


def include_router(app):
    app.include_router(router)
