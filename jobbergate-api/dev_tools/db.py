"""
Provide commands for interating with local databases.
"""

import json
import subprocess

import docker_gadgets
import typer
from loguru import logger

from jobbergate_api.config import settings
from jobbergate_api.storage import build_db_url

app = typer.Typer()


@app.command()
def login(test: bool = typer.Option(False, help="Log into the test database instead")):
    """
    Log into a local database.
    """
    url = build_db_url(force_test=test)
    logger.debug(f"Logging into database: {url}")
    subprocess.run(["pgcli", url])


@app.command()
def start(test: bool = typer.Option(False, help="Start a test database instead")):
    """
    Start a local postgres database for local development.
    """
    name = "dev-jobbergate-postgres"
    kwargs = dict(
        image="postgres:14.1",
        env=dict(
            POSTGRES_PASSWORD=settings.DATABASE_PSWD,
            POSTGRES_DB=settings.DATABASE_NAME,
            POSTGRES_USER=settings.DATABASE_USER,
        ),
        ports={"5432/tcp": settings.DATABASE_PORT},
    )
    if test:
        kwargs.update(
            env=dict(
                POSTGRES_PASSWORD=settings.TEST_DATABASE_PSWD,
                POSTGRES_DB=settings.TEST_DATABASE_NAME,
                POSTGRES_USER=settings.TEST_DATABASE_USER,
            ),
            ports={"5432/tcp": settings.TEST_DATABASE_PORT},
            tmpfs={"/var/lib/postgresql/data": "rw"},
        )
        name = "test-jobbergate-postgres"

    logger.debug(f"Starting {name} with:\n {json.dumps(kwargs, indent=2)}")

    docker_gadgets.start_service(name, **kwargs)


@app.command()
def start_all():
    """
    Start all local databases.
    """
    start()
    start(test=True)
