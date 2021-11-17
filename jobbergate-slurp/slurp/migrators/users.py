import json

import httpx
from loguru import logger

from slurp.exceptions import SlurpException
from slurp.config import settings


def migrate_users(nextgen_db):
    logger.debug("Getting access token from Auth0")
    auth0_body = dict(
        audience=settings.AUTH0_AUDIENCE,
        client_id=settings.AUTH0_CLIENT_ID,
        client_secret=settings.AUTH0_CLIENT_SECRET,
        grant_type="client_credentials",
    )
    auth0_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    response = httpx.post(auth0_url, data=auth0_body)
    SlurpException.require_condition(
        response.status_code == 200,
        f"Failed to get auth token from Auth0: {response.text}"
    )
    with SlurpException.handle_errors("Malformed response payload from Auth0"):
        token = response.json()['access_token']
    token_header = dict(Authorization=f'Bearer {token}')

    logger.debug("Fetching users from Auth0")
    response = httpx.get(f"https://{settings.AUTH0_DOMAIN}/api/v2/users", headers=token_header)
    SlurpException.require_condition(
        response.status_code == 200,
        f"Failed to get users from Auth0: {response.text}"
    )
    with SlurpException.handle_errors("Malformed response payload from Auth0"):
        user_map = [(f"legacy--{u['email']}", u["user_id"]) for u in response.json()]

    logger.debug("Creating temp table with user map")
    nextgen_db.execute("""
        create temp table tmp_user_map (
            legacy_user_id text,
            nextgen_user_id text
        )
    """)
    logger.debug("Inserting user map into temp table")
    with nextgen_db.copy("copy tmp_user_map from stdin") as copy:
        for user in user_map:
            result = copy.write_row(user)

    logger.debug("Updating applications with user map")
    result = nextgen_db.execute("""
        update applications
        set application_owner_id = nextgen_user_id
        from tmp_user_map
        where applications.application_owner_id = tmp_user_map.legacy_user_id
    """)
    logger.debug(f"Updated {result.rowcount} applications")

    logger.debug("Updating job_scripts with user map")
    result = nextgen_db.execute("""
        update job_scripts
        set job_script_owner_id = nextgen_user_id
        from tmp_user_map
        where job_scripts.job_script_owner_id = tmp_user_map.legacy_user_id
    """)
    logger.debug(f"Updated {result.rowcount} job_scripts")

    logger.debug("Updating job_submissions with user map")
    result = nextgen_db.execute("""
        update job_submissions
        set job_submission_owner_id = nextgen_user_id
        from tmp_user_map
        where job_submissions.job_submission_owner_id = tmp_user_map.legacy_user_id
    """)
    logger.debug(f"Updated {result.rowcount} job_submissions")
