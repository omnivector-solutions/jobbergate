from buzz import handle_errors
from loguru import logger

from jobbergate_cli.auth import load_tokens_from_cache, validate_token_and_extract_identity
from jobbergate_cli.end_to_end_testing.applications import Applications
from jobbergate_cli.end_to_end_testing.job_scripts import JobScripts
from jobbergate_cli.end_to_end_testing.job_submission import JobSubmissions


def validate_access_token():

    logger.info("Start validating access token")

    with handle_errors("Please, login in to Jobbergate. Failed to validate access token."):
        token_set = load_tokens_from_cache()
        validate_token_and_extract_identity(token_set)


def main():

    logger.info("Starting end-to-end testing")

    validate_access_token()

    app_list = [
        Applications(),
        JobScripts(),
        JobSubmissions(),
    ]

    for app in app_list:

        app.create()
        app.get()
        app.update()
        app.list()

    logger.success("Completed end-to-end testing")


if __name__ == "__main__":
    main()
