from armasec import TokenPayload
from fastapi import Depends
from loguru import logger
from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest, JobTemplateResponse
from jobbergate_api.apps.job_script_templates.models import job_script_templates_table
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import database
from jobbergate_api.security import IdentityClaims, guard


async def create(
    incoming_data: JobTemplateCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.APPLICATIONS_EDIT)),
) -> JobTemplateResponse:
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    logger.debug(f"Identity claims: {identity_claims}")
    create_dict = dict(
        **incoming_data.dict(exclude_unset=True),
        owner_email=identity_claims.email,
    )
    insert_query = job_script_templates_table.insert().returning(job_script_templates_table)
    inserted_row = await database.fetch_one(query=insert_query, values=create_dict)
    return JobTemplateResponse(**inserted_row)


def read():
    pass


def list():
    pass


def update():
    pass


def delete():
    pass
