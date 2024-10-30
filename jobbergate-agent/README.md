# Jobbergate-agent

## Install the package

To install the package from Pypi simply run `pip install jobbergate-agent`.

## Setup parameters

1. Setup dependencies

    Dependencies and environment are managed in the project by [Poetry](https://python-poetry.org/). To initiate the development environment run:

    ```bash
    make install
    ```

2. Setup `.env` parameters

    ```bash
    JOBBERGATE_AGENT_BASE_API_URL="<base-api-url>"
    JOBBERGATE_AGENT_X_SLURM_USER_NAME="<sbatch-user-name>"
    JOBBERGATE_AGENT_SENTRY_DSN="<sentry-dsn-key>"
    JOBBERGATE_AGENT_OIDC_DOMAIN="<OIDC-domain>"
    JOBBERGATE_AGENT_OIDC_CLIENT_ID="<OIDC-app-client-id>"
    JOBBERGATE_AGENT_OIDC_CLIENT_SECRET="<OIDC-app-client-secret>"
    ```

    **Note**: `JOBBERGATE_AGENT_SENTRY_DSN` is optional. If you do not pass it the agent understands Sentry will not be used.

## Local usage example

1. Run app

    ```bash
    jg-run
    ```

    **Note**: this command assumes you're inside a virtual environment in which the package is installed.

    **Note**: beware you should care about having the same user name you're using to run the code in the slurmctld node. For example, if `cluster_agent` will run the `make run` command then the slurmctld node also must have a user called `cluster_agent`.
