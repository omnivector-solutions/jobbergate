import subprocess

import docker_gadgets
import typer

from jobbergate_api.config import settings
from jobbergate_api.storage import build_db_url

app = typer.Typer()


@app.command()
def login(test: bool = typer.Option(False, help="Log into the test database instead"),):
    """
    Logs into a local database.
    """
    subprocess.run(["pgcli", build_db_url(force_test=test)])


@app.command()
def start_dev():
    """
    Starts a local postgres database for local development.
    """
    docker_gadgets.start_service(
        "dev-jobbergate-postgres",
        image="postgres:14.1",
        env=dict(
            POSTGRES_PASSWORD=settings.DATABASE_PSWD,
            POSTGRES_DATABASE=settings.DATABASE_NAME,
            POSTGRES_USER=settings.DATABASE_USER,
        ),
        ports={"5432/tcp": settings.DATABASE_PORT},
    )


@app.command()
def start_test():
    docker_gadgets.start_service(
        "test-jobbergate-postgres",
        image="postgres:14.1",
        env=dict(
            POSTGRES_PASSWORD=settings.TEST_DATABASE_PSWD,
            POSTGRES_DATABASE=settings.TEST_DATABASE_NAME,
            POSTGRES_USER=settings.TEST_DATABASE_USER,
        ),
        ports={"5432/tcp": settings.TEST_DATABASE_PORT},
        tmpfs={"/var/lib/postgresql/data": "rw"},
    )


@app.command()
def start_all():
    start_dev()
    start_test()
