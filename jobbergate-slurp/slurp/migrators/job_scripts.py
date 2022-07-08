"""
Provides logic for migrating job_script data from legacy db to nextgen db.
"""

from loguru import logger
from report_on_interval import report_on_interval

def _batch_insert(db, value_sets, job_script_ids, job_scripts_map):
    result = db.execute(
        """
        insert into job_scripts (
            job_script_name,
            job_script_description,
            job_script_data_as_string,
            job_script_owner_email,
            application_id,
            created_at,
            updated_at
        )
        values {}
        returning id
        """.format(
            ','.join(
                db.mogrify(
                    "({})".format(','.join(['%s'] * len(values))),
                    values,
                )
                for values in value_sets
            )
        )
    )
    inserted_ids = [r["id"] for r in result.fetchall()]
    for (old_id, new_id) in zip(job_script_ids, inserted_ids):
        job_scripts_map[old_id] = new_id
    value_sets.clear()
    job_script_ids.clear()


def migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, application_map):
    """
    Inserts job_script data to nextgen database.

    Given a list of legacy job_scripts, a user map, and an applicaiton map, create
    records in the nextgen database for each job_script.

    :returns: An dict mapping legacy job_script ids to nextgen job_script ids
    """
    job_scripts_map = {}
    logger.info("Migrating job_scripts to nextgen database")
    script_count = len(legacy_job_scripts)
    interval = min(1000, script_count // 100)
    value_sets = []
    job_script_ids = []


    for (i, job_script) in enumerate(legacy_job_scripts):
        owner_email = user_map[job_script["job_script_owner_id"]]["email"]
        nextgen_application_id = application_map[job_script["application_id"]]
        value_sets.append(
            (
                job_script["job_script_name"],
                job_script["job_script_description"],
                job_script["job_script_data_as_string"],
                owner_email,
                nextgen_application_id,
                job_script["created_at"],
                job_script["updated_at"],
            )
        )
        job_script_ids.append(job_script["id"])

        if i % interval == 0 and i > 0:
            _batch_insert(nextgen_db, value_sets, job_script_ids, job_scripts_map)
            logger.debug(f"{i}/{script_count} job scripts migrated")

    _batch_insert(nextgen_db, value_sets, job_script_ids, job_scripts_map)

    logger.success("Finished migrating job_scripts")
    return job_scripts_map
