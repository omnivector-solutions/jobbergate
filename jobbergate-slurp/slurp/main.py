"""
The main slurp application.

Provides a Typer app and associated commands.
"""
import subprocess

import typer
from loguru import logger

from slurp.connections import build_url, db
from slurp.migrators.applications import mark_uploaded, migrate_applications
from slurp.migrators.job_scripts import migrate_job_scripts
from slurp.migrators.job_submissions import migrate_job_submissions
from slurp.pull_legacy import pull_applications, pull_job_scripts, pull_job_submissions, pull_users
from slurp.s3_ops import build_managers, transfer_s3

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
    logger.info("Clearing out nextgen database")
    with db(is_legacy=False) as nextgen_db:
        logger.info("Truncating job_submissions")
        nextgen_db.execute("truncate job_submissions cascade")

        logger.info("Truncating job_scripts")
        nextgen_db.execute("truncate job_scripts cascade")

        logger.info("Truncating applications")
        nextgen_db.execute("truncate applications cascade")

        logger.info("Remember to clean S3 objects manually, if necessary")
    logger.success("Finished clearing!")


@app.command()
def migrate(
    ignore_submissions: bool = typer.Option(
        False, help="Ignores the Submissions Table when copying data from the legacy database."
    ),
):
    """
    Migrates data from the legacy database to the nextgen database.
    """
    logger.info("Migrating jobbergate data from legacy to nextgen database")
    s3man = build_managers()
    with db(is_legacy=True) as legacy_db, db(is_legacy=False) as nextgen_db:
        user_map = pull_users(legacy_db)

        legacy_applications = pull_applications(legacy_db)
        applications_map = migrate_applications(nextgen_db, legacy_applications, user_map)

        legacy_job_scripts = pull_job_scripts(legacy_db)
        job_scripts_map = migrate_job_scripts(
            nextgen_db, legacy_job_scripts, user_map, applications_map, s3man.jobscripts
        )

        if not ignore_submissions:
            legacy_job_submissions = pull_job_submissions(legacy_db)
            migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map, job_scripts_map)

        transferred_ids = transfer_s3(s3man.applications, applications_map)

        mark_uploaded(nextgen_db, transferred_ids)

    logger.success("Finished migration!")
