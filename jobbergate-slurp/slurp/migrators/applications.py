from loguru import logger
import snick

from slurp.connections import db


def migrate_applications(nextgen_db, legacy_applications, user_map):
    application_map = {}
    logger.debug("Inserting applications to nextgen database")
    for application in legacy_applications:
        legacy_email = user_map[application["application_owner_id"]]["email"]
        nextgen_interim_owner_id = f"legacy--{legacy_email}"

        result = nextgen_db.execute(
            """
            insert into applications (
                application_name,
                application_identifier,
                application_description,
                application_owner_id,
                application_file,
                application_config,
                created_at,
                updated_at
            )
            values (
                %(name)s,
                %(identifier)s,
                %(description)s,
                %(owner_id)s,
                %(file)s,
                %(config)s,
                %(created)s,
                %(updated)s
            )
            returning id
            """,
            dict(
                name=application["application_name"],
                identifier=application["application_identifier"],
                description=application["application_description"],
                owner_id=nextgen_interim_owner_id,
                file=application["application_file"],
                config=application["application_config"],
                created=application["created_at"],
                updated=application["updated_at"],
            )
        )
        application_map[application["id"]] = nextgen_db.fetchone()["id"]
    logger.debug("Finished migrating applications")
    return application_map
