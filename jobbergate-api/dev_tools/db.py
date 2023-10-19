"""Provide commands for interacting with local databases."""

import subprocess

import typer
from loguru import logger

from alembic.command import revision as sqla_migrate
from alembic.command import upgrade as sqla_upgrade
from alembic.config import Config
from jobbergate_api.storage import build_db_url

app = typer.Typer()


@app.command()
def login(test: bool = typer.Option(False, help="Log into the test database.")):
    """Log into a local database."""
    url = build_db_url(force_test=test, asynchronous=False)
    logger.debug(f"Logging into database: {url}")
    subprocess.run(["pgcli", url])


@app.command()
def migrate(
    message: str = typer.Option("Unlabeled migration", help="The message to attach to the migration."),
    blank: bool = typer.Option(False, help="Produce a blank migration"),
):
    """Create alembic migrations for a local database."""
    logger.debug(f"Creating migration with message: {message}")
    config = Config(file_="alembic/alembic.ini")
    sqla_migrate(config, message=message, autogenerate=not blank)


@app.command()
def upgrade(target: str = typer.Option("head", help="The migration to which the db should be upgraded.")):
    """Apply alembic migrations to a local database."""
    logger.debug("Upgrading database...")

    config = Config(file_="alembic/alembic.ini")
    sqla_upgrade(config, target)
