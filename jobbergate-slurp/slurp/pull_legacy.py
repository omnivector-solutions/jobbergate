from loguru import logger

from slurp.connections import db


def pull_users(legacy_db):
    user_map = {}
    logger.debug("Fetching users from legacy database")
    legacy_db.execute("select id, first_name, last_name, email from user_user")
    for (i, record) in enumerate(legacy_db.fetchall()):
        user_map[record['id']] = {k: v for (k, v) in record.items() if k != 'id'}
    return user_map


def pull_applications(legacy_db):
    logger.debug("Fetching applications from legacy database")
    result = legacy_db.execute("select * from applications")
    logger.debug(f"Fetched {result.rowcount} applications")
    return result.fetchall()


def pull_job_scripts(legacy_db):
    logger.debug("Fetching job_scripts from legacy database")
    result = legacy_db.execute("select * from job_scripts")
    logger.debug(f"Fetched {result.rowcount} job_scripts")
    return result.fetchall()


def pull_job_submissions(legacy_db):
    logger.debug("Fetching job_submissions from legacy database")
    result = legacy_db.execute("select * from job_submissions")
    logger.debug(f"Fetched {result.rowcount} job_submissions")
    return result.fetchall()
