"""
Provides methods that pull data from the legacy database.
"""
from loguru import logger


def pull_users(legacy_db):
    """
    Pull all user data.

    :returns: A user map dictionary keyed by legacy user id
    """
    user_map = {}
    logger.debug("Fetching users from legacy database")
    legacy_db.execute("select id, first_name, last_name, email from user_user")
    for (i, record) in enumerate(legacy_db.fetchall()):
        user_map[record['id']] = {k: v for (k, v) in record.items() if k != 'id'}
    return user_map


def pull_applications(legacy_db):
    """
    Pull all application data.
    """
    logger.debug("Fetching applications from legacy database")
    result = legacy_db.execute("select * from applications")
    logger.debug(f"Fetched {result.rowcount} applications")
    return result.fetchall()


def pull_job_scripts(legacy_db):
    """
    Pull all job_script data.
    """
    batch_size = 500
    logger.debug("Fetching job_scripts from legacy database")
    result = legacy_db.execute("select * from job_scripts")
    while True:
        logger.debug(f"Fetching next {batch_size} job_scripts")
        records = result.fetchmany(batch_size)
        if not records:
            break
        yield records


def pull_job_submissions(legacy_db):
    """
    Pull all job_submission data.
    """
    batch_size = 500
    logger.debug("Fetching job_submissions from legacy database")
    result = legacy_db.execute("select * from job_submissions")
    while True:
        logger.debug(f"Fetching next {batch_size} job_submissions")
        records = result.fetchmany(batch_size)
        if not records:
            break
        yield records
