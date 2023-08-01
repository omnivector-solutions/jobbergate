"""
Provides logic for migrating application data from legacy db to nextgen db.
"""
from loguru import logger

from slurp.batch import batch


def migrate_applications(nextgen_db, legacy_applications, user_map, batch_size=1000):
    """
    Inserts application data to nextgen database.

    Given a list of legacy applications and a user map, create records in the
    nextgen database for each application.
    """
    logger.info("Inserting applications to nextgen database")
    for application_batch in batch(legacy_applications, batch_size):
        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(id)s,
                        %(name)s,
                        %(identifier)s,
                        %(description)s,
                        %(owner_email)s,
                        %(created)s,
                        %(updated)s
                            )
                    """,
                    dict(
                        id=application["id"],
                        name=application["application_name"],
                        identifier=application["application_identifier"],
                        description=application["application_description"],
                        owner_email=user_map[application["application_owner_id"]]["email"],
                        created=application["created_at"],
                        updated=application["updated_at"],
                    ),
                )
                for application in application_batch
            ]
        )

        nextgen_db.execute(
            """
            insert into job_script_templates (
                id,
                name,
                identifier,
                description,
                owner_email,
                created_at,
                updated_at
            )
            values {}
            """.format(
                mogrified_params
            ),
        )
        logger.success(f"Finished batch of {batch_size}")

    logger.success("Finished migrating applications")


def mark_uploaded(nextgen_db, ids):
    """
    Marks application rows as uploaded.

    Given a list of nextgen application_ids, mark each as uploaded.
    """
    logger.info("Marking uploaded applications in nextgen database")

    batch_size = 1000
    id_count = len(ids)
    batch_start = 0
    while batch_start < id_count:
        batch_end = min(batch_start + batch_size, id_count)
        logger.debug(f"Marking application {batch_start} through {batch_end} of {id_count}")
        batch = ids[batch_start:batch_end]
        nextgen_db.execute(
            """
            update applications
            set application_uploaded = true
            where id = any(%s)
            """,
            (batch,),
        )

        batch_start += batch_size

    logger.success("Finished marking uploaded applications")
