"""
Provides logic for migrating job_script data from legacy db to nextgen db.
"""

from loguru import logger


def migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, application_map, s3man):
    """
    Inserts job_script data to nextgen database.

    Given a list of legacy job_scripts, a user map, and an application map, create
    records in the nextgen database for each job_script.

    :returns: An dict mapping legacy job_script ids to nextgen job_script ids
    """
    job_scripts_map = {}
    logger.info("Migrating job_scripts to nextgen database")

    for job_script in legacy_job_scripts:
        owner_email = user_map[job_script["job_script_owner_id"]]["email"]
        nextgen_application_id = application_map[job_script["application_id"]]

        result = nextgen_db.execute(
            """
            insert into job_scripts (
                job_script_name,
                job_script_description,
                job_script_owner_email,
                application_id,
                created_at,
                updated_at
            )
            values (
                %(name)s,
                %(description)s,
                %(owner_email)s,
                %(application_id)s,
                %(created)s,
                %(updated)s
            )
            returning id
            """,
            dict(
                name=job_script["job_script_name"],
                description=job_script["job_script_description"],
                owner_email=owner_email,
                application_id=nextgen_application_id,
                created=job_script["created_at"],
                updated=job_script["updated_at"],
            ),
        )

        nextgen_jobscript_id = result.fetchone()["id"]
        job_scripts_map[job_script["id"]] = nextgen_jobscript_id

        try:
            job_script_files = s3man.nextgen.get_from_json(
                job_script["job_script_data_as_string"],
            )
        except (ValueError, TypeError):
            logger.error(
                f"Error getting job script content {nextgen_jobscript_id=}: {job_script['job_script_data_as_string']}"
            )
        else:
            job_script_files.write_to_s3(nextgen_jobscript_id)

    logger.success("Finished migrating job_scripts")
    return job_scripts_map
