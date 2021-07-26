"""
Router for the JobScript resource.
"""
import json
import tarfile
import tempfile
from datetime import datetime
from io import BytesIO, StringIO
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from jinja2 import Template

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.auth.authentication import Permission, get_current_user
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_scripts.schemas import JobScript, JobScriptRequest
from jobbergateapi2.apps.permissions.routers import resource_acl_as_list
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.config import settings
from jobbergateapi2.pagination import Pagination
from jobbergateapi2.storage import database

S3_BUCKET = f"jobbergateapi2-{settings.SERVERLESS_STAGE}-{settings.SERVERLESS_REGION}-resources"
router = APIRouter()


async def job_scripts_acl_as_list():
    """
    Return the permissions as list for the JobScript resoruce.
    """
    return await resource_acl_as_list("job_script")


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
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


def get_s3_object_as_tarfile(current_user_id, application_id):
    """
    Return the tarfile of a S3 object.
    """
    s3_client = boto3.client("s3")
    application_location = (
        f"{settings.S3_BASE_PATH}/{current_user_id}/applications/{application_id}/jobbergate.tar.gz"
    )
    try:
        s3_application_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=application_location)
    except BotoCoreError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found for user={current_user_id} in S3",
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
    for key, value in param_dict.items():
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
    "/job-scripts/", status_code=status.HTTP_201_CREATED, description="Endpoint for job_script creation"
)
async def job_script_create(
    job_script_name: str = Form(...),
    job_script_description: Optional[str] = Form(""),
    application_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    upload_file: UploadFile = File(...),
    sbatch_params: Optional[List[str]] = Form(None),
    param_dict: Optional[str] = Form(None),
    acls: list = Permission("create", job_scripts_acl_as_list),
):
    """
    Create a new job script.

    Make a post request to this endpoint with the required values to create a new job script.
    """
    param_dict = json.loads(param_dict)
    query = applications_table.select().where(applications_table.c.id == application_id)
    raw_application = await database.fetch_one(query)

    if not raw_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found.",
        )
    application = Application.parse_obj(raw_application)
    s3_application_tar = get_s3_object_as_tarfile(current_user.id, application.id)

    job_script_data_as_string = build_job_script_data_as_string(s3_application_tar, param_dict)

    if sbatch_params:
        job_script_data_as_string = inject_sbatch_params(job_script_data_as_string, sbatch_params)

    job_script = JobScriptRequest(
        job_script_name=job_script_name,
        job_script_description=job_script_description,
        job_script_data_as_string=job_script_data_as_string,
        job_script_owner_id=current_user.id,
        application_id=application_id,
    )

    async with database.transaction():
        try:
            query = job_scripts_table.insert()
            values = job_script.dict()
            job_script_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return JobScript(id=job_script_created_id, **job_script.dict())


@router.get(
    "/job-scripts/{job_script_id}", description="Endpoint to get a job_script", response_model=JobScript
)
async def job_script_get(
    job_script_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    acls: list = Permission("view", job_scripts_acl_as_list),
):
    """
    Return the job_script given it's id.
    """
    query = job_scripts_table.select().where(job_scripts_table.c.id == job_script_id)
    raw_job_script = await database.fetch_one(query)

    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobScript with id={job_script_id} not found.",
        )
    job_script = JobScript.parse_obj(raw_job_script)
    return job_script


@router.get("/job-scripts/", description="Endpoint to list job_scripts", response_model=List[JobScript])
async def job_script_list(
    p: Pagination = Depends(),
    all: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    acls: list = Permission("view", job_scripts_acl_as_list),
):
    """
    List job_scripts for the authenticated user.
    """
    if all:
        query = job_scripts_table.select().limit(p.limit).offset(p.skip)
    else:
        query = (
            job_scripts_table.select()
            .where(job_scripts_table.c.job_script_owner_id == current_user.id)
            .limit(p.limit)
            .offset(p.skip)
        )
    raw_job_scripts = await database.fetch_all(query)
    job_scripts = [JobScript.parse_obj(x) for x in raw_job_scripts]

    return job_scripts


@router.delete(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job script",
)
async def job_script_delete(
    current_user: User = Depends(get_current_user),
    job_script_id: int = Query(..., description="id of the job script to delete"),
    acls: list = Permission("delete", job_scripts_acl_as_list),
):
    """
    Delete job_script given its id.
    """
    where_stmt = job_scripts_table.c.id == job_script_id

    get_query = job_scripts_table.select().where(where_stmt)
    raw_job_script = await database.fetch_one(get_query)
    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobScript with id={job_script_id} not found.",
        )

    delete_query = job_scripts_table.delete().where(where_stmt)
    await database.execute(delete_query)


@router.put(
    "/job-scripts/{job_script_id}",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to update a job_script given the id",
    response_model=JobScript,
)
async def job_script_update(
    job_script_id: int = Query(...),
    job_script_name: Optional[str] = Form(None),
    job_script_description: Optional[str] = Form(None),
    job_script_data_as_string: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    acls: list = Permission("update", job_scripts_acl_as_list),
):
    """
    Update a job_script given its id.
    """
    query = job_scripts_table.select().where(job_scripts_table.c.id == job_script_id)
    raw_job_script = await database.fetch_one(query)

    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobScript with id={job_script_id} not found.",
        )
    job_script_data = JobScript.parse_obj(raw_job_script)

    if job_script_name is not None:
        job_script_data.job_script_name = job_script_name
    if job_script_description is not None:
        job_script_data.job_script_description = job_script_description
    if job_script_data_as_string is not None:
        job_script_data.job_script_data_as_string = job_script_data_as_string

    job_script_data.updated_at = datetime.utcnow()

    values = {
        "job_script_name": job_script_data.job_script_name,
        "job_script_description": job_script_data.job_script_description,
        "job_script_data_as_string": job_script_data.job_script_data_as_string,
        "updated_at": job_script_data.updated_at,
    }
    validated_values = {key: value for key, value in values.items() if value is not None}

    q_update = (
        job_scripts_table.update().where(job_scripts_table.c.id == job_script_id).values(validated_values)
    )
    async with database.transaction():
        try:
            await database.execute(q_update)
        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    query = job_scripts_table.select(job_scripts_table.c.id == job_script_id)
    return JobScript.parse_obj(await database.fetch_one(query))


def include_router(app):
    app.include_router(router)
