"""
Provides logic for migrating job_script data from legacy db to nextgen db.
"""

from loguru import logger

from slurp.batch import batch


def migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, batch_size=1000):
    """
    Inserts job_script data to nextgen database.

    Given a list of legacy job_scripts, a user map, and an application map, create
    records in the nextgen database for each job_script.
    """
    logger.info("Migrating job_scripts to nextgen database")

    for job_script_batch in batch(legacy_job_scripts, batch_size):

        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(id)s,
                        %(name)s,
                        %(description)s,
                        %(owner_email)s,
                        %(application_id)s,
                        %(created)s,
                        %(updated)s
                    )
                    """,
                    dict(
                        id=job_script["id"],
                        name=job_script["job_script_name"],
                        description=job_script["job_script_description"],
                        owner_email=user_map[job_script["job_script_owner_id"]]["email"],
                        application_id=job_script["application_id"],
                        created=job_script["created_at"],
                        updated=job_script["updated_at"],
                    ),
                )
                for job_script in job_script_batch
            ]
        )

        nextgen_db.execute(
            """
            insert into job_scripts (
                id,
                job_script_name,
                job_script_description,
                job_script_owner_email,
                application_id,
                created_at,
                updated_at
            )
            values {}
            """.format(mogrified_params),
        )

    logger.success(f"Finished migrating job_scripts")


def transfer_job_script_files():
    pass
    # legacy_id_empty_jobscript = set()
        # nextgen_jobscript_ids = result.fetchone()["id"]
        # job_scripts_map[job_script["id"]] = nextgen_jobscript_id

#         try:
#             job_script_files = s3man.nextgen.get_from_json(
#                 job_script["job_script_data_as_string"],
#             )
#         except (ValueError, TypeError):
#             logger.error(
#                 f"Error getting job script content {nextgen_jobscript_id=}: {job_script['job_script_data_as_string']}"
#             )
#         else:
#             if not job_script_files.main_file:
#                 logger.warning(
#                     f"Empty job script content ({nextgen_jobscript_id=}; legacy_jobscript_id={job_script['id']})"
#                 )
#                 legacy_id_empty_jobscript.add(job_script["id"])
#             job_script_files.write_to_s3(nextgen_jobscript_id)
#     logger.warning(f"The following legacy ids are empty job-scripts: {legacy_id_empty_jobscript}")
#     logger.debug(f"Job_script map: {job_scripts_map}")
