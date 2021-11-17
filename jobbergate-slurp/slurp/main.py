"""
The main slurp application.

Provides a Typer app and associated commands.
"""
import subprocess
from loguru import logger

import snick
import typer

from slurp.config import settings
from slurp.connections import db, build_url
from slurp.migrators.applications import migrate_applications
from slurp.migrators.job_scripts import migrate_job_scripts
from slurp.migrators.job_submissions import migrate_job_submissions
from slurp.migrators.users import migrate_users
from slurp.pull_legacy import pull_users, pull_applications, pull_job_scripts, pull_job_submissions

app = typer.Typer()


@app.command()
def login(is_legacy: bool = False):
    """
    Runs an interactive postgres shell connected to either legacy or nextgen db.
    """
    subprocess.run(["pgcli", build_url(is_legacy=is_legacy)])


@app.command()
def clear_nextgen_db():
    """
    Clears out the tables of the nextgen database.
    """
    logger.debug("Clearing out nextgen database")
    with db(is_legacy=False) as nextgen_db:
        logger.debug("Truncating job_submissions")
        nextgen_db.execute("truncate job_submissions cascade")

        logger.debug("Truncating job_scripts")
        nextgen_db.execute("truncate job_scripts cascade")

        logger.debug("Truncating applications")
        nextgen_db.execute("truncate applications cascade")
    logger.debug("Finished clearing!")


@app.command()
def migrate():
    """
    Migrates data from the legacy database to the nextgen database.
    """
    logger.debug("Migrating jobbergate data from legacy to nextgen database")
    with db(is_legacy=True) as legacy_db, db(is_legacy=False) as nextgen_db:
        user_map = pull_users(legacy_db)

        legacy_applications = pull_applications(legacy_db)
        applications_map = migrate_applications(nextgen_db, legacy_applications, user_map)

        legacy_job_scripts = pull_job_scripts(legacy_db)
        job_scripts_map = migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, applications_map)

        legacy_job_submissions = pull_job_submissions(legacy_db)
        migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map, job_scripts_map)

    logger.debug("Finished migration!")


@app.command()
def update_users():
    """
    Updates owner ids in the nextgen database.

    Connects to the Auth0 admin api to pull nextgen users and attemtps to match them
    to the legacy users pulled in during migration.
    """
    logger.debug("Update users")
    with db(is_legacy=False) as nextgen_db:
        migrate_users(nextgen_db)
    logger.debug("Finished updating users")
