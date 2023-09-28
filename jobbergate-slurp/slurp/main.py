"""
The main slurp application.

Provides a Typer app and associated commands.
"""
import asyncio
from datetime import datetime
import subprocess

import typer
from loguru import logger

from slurp.connections import build_url, db, reset_id_seq
from slurp.migrators.applications import mark_uploaded, migrate_applications
from slurp.migrators.job_scripts import migrate_job_scripts, transfer_job_script_files
from slurp.migrators.job_submissions import migrate_job_submissions
from slurp.pull_legacy import pull_applications, pull_job_scripts, pull_job_submissions, pull_users
from slurp.s3_ops import transfer_application_files

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
        for table in (
            "job_submissions",
            "job_script_files",
            "job_scripts",
            "job_script_template_files",
            "workflow_files",
            "job_script_templates",
        ):
            logger.info(f"Truncating {table}")
            nextgen_db.execute(f"truncate {table} cascade")

    logger.info("Remember to clean S3 objects manually, if necessary")
    logger.success("Finished clearing!")

def main_task(ignore_submissions):
    with db(is_legacy=True, name="slurp") as legacy_db, db(is_legacy=False) as nextgen_db:
        # user_map = pull_users(legacy_db)

        legacy_applications = pull_applications(legacy_db)
        # migrate_applications(nextgen_db, legacy_applications, user_map)
        # reset_id_seq(nextgen_db, "job_script_templates")

    asyncio.run(transfer_application_files(legacy_applications, db))

    # with db(is_legacy=True, name="slurp") as legacy_db:
    #     user_map = pull_users(legacy_db)
    #     for legacy_job_scripts in pull_job_scripts(legacy_db):
    #         with db(is_legacy=False) as nextgen_db:
    #             migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map)
    #             asyncio.run(transfer_job_script_files(legacy_job_scripts, nextgen_db))
    #     reset_id_seq(nextgen_db, "job_scripts")

    #     if not ignore_submissions:
    #         for legacy_job_submissions in pull_job_submissions(legacy_db):
    #             migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map)
    #         reset_id_seq(nextgen_db, "job_submissions")


@app.command()
def migrate(
    ignore_submissions: bool = typer.Option(
        False, help="Ignores the Submissions Table when copying data from the legacy database."
    ),
):
    """
    Migrates data from the legacy database to the nextgen database.
    """

    timestamp = datetime.now().replace(microsecond=0).isoformat()
    logger.add(f"file_{timestamp}.log")
    logger.info("Migrating jobbergate data from legacy to nextgen database")

    main_task(ignore_submissions)

    # while True:
    #     try:
    #         main_task(ignore_submissions)
    #     except (SystemExit, KeyboardInterrupt):
    #         break
    #     except Exception as e:
    #         logger.error("An error occurred. Retrying... -- {}", str(e))

    logger.success("Finished migration!")
