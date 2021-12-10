"""
The main slurp application.

Provides a Typer app and associated commands.
"""
import subprocess
from loguru import logger

import typer

from slurp.config import DatabaseEnv
from slurp.connections import db, build_url
from slurp.exceptions import SlurpException
from slurp.migrators.applications import migrate_applications
from slurp.migrators.job_scripts import migrate_job_scripts
from slurp.migrators.job_submissions import migrate_job_submissions
from slurp.mirror import reflect
from slurp.pull_legacy import pull_users, pull_applications, pull_job_scripts, pull_job_submissions
from slurp.s3_ops import S3Manager, transfer_s3

app = typer.Typer()


@app.command()
def login(is_legacy: bool = False):
    """
    Runs an interactive postgres shell connected to either legacy or nextgen db.
    """
    subprocess.run(["pgcli", build_url(is_legacy=is_legacy)])


@app.command()
def clear(db_env: DatabaseEnv = typer.Argument(DatabaseEnv.NEXTGEN)):
    """
    Clears out the tables of the nextgen database.
    """
    SlurpException.require_condition(
        db_env is not DatabaseEnv.LEGACY,
        "Cannot clear legacy database",
    )
    logger.debug(f"Clearing out {db_env} database")
    s3man = S3Manager(db_env=db_env)
    with db(db_env=db_env) as target_db:
        logger.debug("Truncating job_submissions")
        target_db.execute("truncate job_submissions cascade")

        logger.debug("Truncating job_scripts")
        target_db.execute("truncate job_scripts cascade")

        logger.debug("Truncating applications")
        target_db.execute("truncate applications cascade")

        logger.debug("Clearing S3 objects")
        s3man.clear_bucket()
    logger.debug("Finished clearing!")


@app.command()
def migrate():
    """
    Migrates data from the legacy database to the nextgen database.
    """
    logger.debug("Migrating jobbergate data from legacy to nextgen database")
    legacy_s3man = S3Manager(db_env=DatabaseEnv.LEGACY)
    nextgen_s3man = S3Manager(db_env=DatabaseEnv.NEXTGEN)
    with db(db_env=DatabaseEnv.LEGACY) as legacy_db, db(db_env=DatabaseEnv.NEXTGEN) as nextgen_db:
        user_map = pull_users(legacy_db)

        legacy_applications = pull_applications(legacy_db)
        applications_map = migrate_applications(nextgen_db, legacy_applications, user_map)

        legacy_job_scripts = pull_job_scripts(legacy_db)
        job_scripts_map = migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, applications_map)

        legacy_job_submissions = pull_job_submissions(legacy_db)
        migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map, job_scripts_map)

        transfer_s3(legacy_s3man, nextgen_s3man, applications_map)

    logger.debug("Finished migration!")


@app.command()
def mirror():
    """
    Mirrors data from nextgen_db to mirror_db.
    """
    logger.debug("Mirroring jobbergate data from nextgen to mirror database")
    nextgen_s3man = S3Manager(db_env=DatabaseEnv.NEXTGEN)
    mirror_s3man = S3Manager(db_env=DatabaseEnv.MIRROR)
    with db(db_env=DatabaseEnv.NEXTGEN) as nextgen_db, db(db_env=DatabaseEnv.MIRROR) as mirror_db:
        reflect(nextgen_db, mirror_db)
        # transfer_s3(legacy_s3man, nextgen_s3man, applications_map)

    logger.debug("Finished reflection!")
