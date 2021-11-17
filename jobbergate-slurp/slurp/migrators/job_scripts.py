"""
Provides logic for migrating job_script data from legacy db to nextgen db.
"""

from loguru import logger
import snick

from slurp.connections import db


def migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, application_map):
    """
    Inserts job_script data to nextgen database.

    Given a list of legacy job_scripts, a user map, and an applicaiton map, create
    records in the nextgen database for each job_script.

    :returns: An dict mapping legacy job_script ids to nextgen job_script ids
    """
    job_scripts_map = {}
    logger.debug("Migrating job_scripts to nextgen database")
    for job_script in legacy_job_scripts:
        legacy_email = user_map[job_script["job_script_owner_id"]]["email"]
        nextgen_interim_owner_id = f"legacy--{legacy_email}"
        nextgen_application_id = application_map[job_script["application_id"]]

        result = nextgen_db.execute(
            """
            insert into job_scripts (
                job_script_name,
                job_script_description,
                job_script_data_as_string,
                job_script_owner_id,
                application_id,
                created_at,
                updated_at
            )
            values (
                %(name)s,
                %(description)s,
                %(data)s,
                %(owner_id)s,
                %(application_id)s,
                %(created)s,
                %(updated)s
            )
            returning id
            """,
            dict(
                name=job_script["job_script_name"],
                description=job_script["job_script_description"],
                data=job_script["job_script_data_as_string"],
                owner_id=nextgen_interim_owner_id,
                application_id=nextgen_application_id,
                created=job_script["created_at"],
                updated=job_script["updated_at"],
            )
        )
        job_scripts_map[job_script["id"]] = result.fetchone()["id"]
    logger.debug("Finished migrating job_scripts")
    return job_scripts_map
