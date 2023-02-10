from pathlib import Path
from typing import Optional
import typer
from buzz import handle_errors
from jobbergate_cli.auth import (
    load_tokens_from_cache,
    validate_token_and_extract_identity,
)
from loguru import logger

from jobbergate_test.applications import Applications
from jobbergate_test.job_scripts import JobScripts
from jobbergate_test.job_submission import JobSubmissions


def validate_access_token():

    logger.info("Start validating access token")

    with handle_errors(
        "Please, login in to Jobbergate. Failed to validate access token."
    ):
        token_set = load_tokens_from_cache()
        validate_token_and_extract_identity(token_set)


def test_jobbergate(
    application_path: Path = typer.Argument(
        Path("..", "examples"),
        help="Path to the application's folder",
        exists=True,
        dir_okay=True,
        resolve_path=True,
    ),
    test_prefix: str = typer.Option(
        Path.cwd().name,
        help="Prefix for the test data",
    ),
):
    """
    High level test suite for the Jobbergate API.

    This test suite will create, get, update and list all the resources in the Jobbergate API,
    including Applications, Job-scripts and Job-submissions.
    """
    logger.info("Starting end-to-end testing")

    validate_access_token()

    app_list = [
        Applications(application_path, test_prefix),
        JobScripts(),
        JobSubmissions(),
    ]

    for app in app_list:

        app.create()
        app.get()
        app.update()
        app.list()

    logger.success("Completed end-to-end testing")


def main():
    typer.run(test_jobbergate)


if __name__ == "__main__":
    main()
