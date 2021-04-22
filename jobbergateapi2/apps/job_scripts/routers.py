"""
Router for the Application resource.
"""
import json
import tarfile
import tempfile
from io import BytesIO, StringIO
from typing import List, Optional

import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from jinja2 import Template

from jobbergateapi2.apps.applications.models import applications_table
from jobbergateapi2.apps.applications.schemas import Application
from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_scripts.schemas import JobScript
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.config import settings
from jobbergateapi2.storage import database

S3_BUCKET = f"jobbergate-api-{settings.SERVERLESS_STAGE}-{settings.SERVERLESS_REGION}-resources"
router = APIRouter()


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: List[str]) -> str:
    """
    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location
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


@router.post("/job-scripts/", status_code=201, description="Endpoint for job_script creation")
async def job_script_create(
    job_script_name: str = Form(...),
    job_script_description: Optional[str] = Form(""),
    job_script_data_as_string: str = Form(...),
    application_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    upload_file: UploadFile = File(...),
    sbatch_params: Optional[List[str]] = Form(None),
    param_dict: Optional[str] = Form(None),
):
    """
    Create new job_script using an authenticated user.
    """
    s3_client = boto3.client("s3")
    param_dict = json.loads(param_dict)
    query = applications_table.select().where(
        (applications_table.c.id == application_id)
        & (applications_table.c.application_owner_id == current_user.id)
    )
    raw_application = await database.fetch_one(query)

    if not raw_application:
        raise HTTPException(
            status_code=422,
            detail=f"Application with id={application_id} not found for user={current_user.id}",
        )
    application = Application.parse_obj(raw_application)

    try:
        support_files_ouput = param_dict["jobbergate_config"].get("supporting_files_output_name")
    except KeyError:
        support_files_ouput = {}
    try:
        supporting_files = param_dict["jobbergate_config"].get("supporting_files")
    except KeyError:
        supporting_files = []

    default_template = [
        default_template := param_dict["jobbergate_config"].get("default_template"),
        "templates/" + default_template,
    ]

    application_location = (
        f"{settings.S3_BASE_PATH}/TEST/applications/{application.id}/jobbergate.tar.gz"
        # f"{S3_BASE_PATH}/{application.owner_id}/applications/{application.id}/jobbergate.tar.gz"
    )
    s3_application_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=application_location)
    s3_application_tar = tarfile.open(fileobj=BytesIO(s3_application_obj["Body"].read()))
    template_files = {}
    for member in s3_application_tar.getmembers():
        if member.name in default_template:
            contentfobj = s3_application_tar.extractfile(member)
            template_files["application.sh"] = contentfobj.read().decode("utf-8")
        if member.name in supporting_files:
            match = [x for x in support_files_ouput if member.name in x]
            contentfobj = s3_application_tar.extractfile(member)
            filename = support_files_ouput[match[0]][0]
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
    job_script_data_as_string = ""
    for key, value in template_files.items():
        template = Template(value)
        rendered_js = template.render(data=param_dict_flat)
        job_script_data_as_string
        template_files[key] = rendered_js

    job_script_data_as_string = json.dumps(template_files)
    if sbatch_params:
        job_script_data_as_string = inject_sbatch_params(job_script_data_as_string, sbatch_params)

    job_script = JobScript(
        job_script_name=job_script_name,
        job_script_description=job_script_description,
        job_script_data_as_string=job_script_data_as_string,
        job_script_owner_id=current_user.id,
        job_script_application_id=application_id,
    )

    async with database.transaction():
        try:
            query = job_scripts_table.insert()
            values = job_script.dict()
            job_script_created_id = await database.execute(query=query, values=values)
            job_script.id = job_script_created_id

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    return job_script


def include_router(app):
    app.include_router(router)
