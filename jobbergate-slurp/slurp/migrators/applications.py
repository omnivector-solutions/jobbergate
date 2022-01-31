"""
Provides logic for migrating application data from legacy db to nextgen db.
"""
from loguru import logger


def migrate_applications(nextgen_db, legacy_applications, user_map):
    """
    Inserts application data to nextgen database.

    Given a list of legacy applications and a user map, create records in the
    nextgen database for each application.

    :returns: An dict mapping legacy application ids to nextgen application ids
    """
    application_map = {}
    logger.debug("Inserting applications to nextgen database")
    for application in legacy_applications:
        owner_email = user_map[application["application_owner_id"]]["email"]

        nextgen_db.execute(
            """
            insert into applications (
                application_name,
                application_identifier,
                application_description,
                application_owner_email,
                application_file,
                application_config,
                application_uploaded,
                created_at,
                updated_at
            )
            values (
                %(name)s,
                %(identifier)s,
                %(description)s,
                %(owner_email)s,
                %(file)s,
                %(config)s,
                false,
                %(created)s,
                %(updated)s
            )
            returning id
            """,
            dict(
                name=application["application_name"],
                identifier=application["application_identifier"],
                description=application["application_description"],
                owner_email=owner_email,
                file=application["application_file"],
                config=application["application_config"],
                created=application["created_at"],
                updated=application["updated_at"],
            )
        )
        application_map[application["id"]] = nextgen_db.fetchone()["id"]
    logger.debug("Finished migrating applications")
    return application_map


def mark_uploaded(nextgen_db, ids):
    """
    Marks application rows as uploaded.

    Given a list of nextgen application_ids, mark each as uploaded.
    """
    logger.debug("Marking uploaded applications in nextgen database")

    nextgen_db.execute(
        """
        update applications
        set application_uploaded = true
        where id in %(ids)
        """,
        dict(ids=ids)
    )
    logger.debug("Finished marking uploaded applications")
