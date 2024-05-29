"""
The main slurp application.

Provides a Typer app and associated commands.
"""

import asyncio
from datetime import datetime
import subprocess
from faker import Faker
import pendulum

import typer
from loguru import logger

from slurp.connections import build_url, db, reset_id_seq
from slurp.migrators.applications import migrate_applications
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

    with db(is_legacy=True) as legacy_db, db(is_legacy=False) as nextgen_db:
        user_map = pull_users(legacy_db)

        legacy_applications = pull_applications(legacy_db)
        migrate_applications(nextgen_db, legacy_applications, user_map)
        reset_id_seq(nextgen_db, "job_script_templates")

        legacy_job_scripts = pull_job_scripts(legacy_db)
        migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map)
        reset_id_seq(nextgen_db, "job_scripts")

        if not ignore_submissions:
            legacy_job_submissions = pull_job_submissions(legacy_db)
            migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map)
            reset_id_seq(nextgen_db, "job_submissions")

    asyncio.run(transfer_application_files(legacy_applications, db))

    asyncio.run(transfer_job_script_files(legacy_job_scripts, db))

    logger.success("Finished migration!")


@app.command()
def fill(
    n: int = typer.Argument(10, help="The number of rows to insert into the table."),
):
    """Fill the database with n rows."""
    logger.debug(f"Inserting {n} rows into the table.")
    fake = Faker()
    today = pendulum.today()
    with db(is_legacy=False) as nextgen_db:
        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(name)s,
                        %(owner_email)s,
                        %(created)s,
                        %(created)s,
                        %(is_archived)s
                    )
                    """,
                    dict(
                        name=fake.name(),
                        owner_email=fake.email(),
                        created=today.add(days=-fake.random_int(1, 365)),
                        is_archived=fake.boolean(chance_of_getting_true=50),
                    ),
                )
                for _ in range(n)
            ]
        )

        nextgen_db.execute(
            """
            insert into job_scripts (
                name,
                owner_email,
                created_at,
                updated_at,
                is_archived
            )
            values {}
            """.format(
                mogrified_params
            ),
        )
        job_script_ids = nextgen_db.execute("select id from job_scripts").fetchall()

        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(job_script_id)s,
                        %(name)s,
                        %(status)s,
                        %(client_id)s,
                        %(owner_email)s,
                        %(created)s,
                        %(created)s
                    )
                    """,
                    dict(
                        job_script_id=parent_id["id"],
                        name=fake.name(),
                        status="CREATED",
                        client_id=fake.uuid4(),
                        owner_email=fake.email(),
                        created=today.add(days=-fake.random_int(1, 365)),
                    ),
                )
                for parent_id in job_script_ids
            ]
        )

        nextgen_db.execute(
            """
            insert into job_submissions (
                job_script_id,
                name,
                status,
                client_id,
                owner_email,
                created_at,
                updated_at
            )
            values {}
            """.format(
                mogrified_params
            ),
        )

    logger.success("Finished filling the table.")
