# Jobbergate-agent

## Install the package

To install the package from Pypi simply run `pip install jobbergate-agent`.

## Setup parameters

1. Setup dependencies
  You can use whenever dependency manager you want to. Just run the command below (and the ones following) on behalf of the manager you prefer.

  ```bash
  make dependencies
  ```

2. Setup `.env` parameters

  ```bash
  JOBBERGATE_AGENT_BASE_API_URL="<base-api-url>"
  JOBBERGATE_AGENT_BASE_SLURMRESTD_URL="<slurmrestd-endpoint>"
  JOBBERGATE_AGENT_X_SLURM_USER_NAME="<slurmrestd-user-name>"
  JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_PATH="/path/to/the/jwt/secret/key"
  JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_STRING="jwt-secret-key-in-plain-text"
  JOBBERGATE_AGENT_SENTRY_DSN="<sentry-dsn-key>"
  JOBBERGATE_AGENT_OIDC_DOMAIN="<OIDC-domain>"
  JOBBERGATE_AGENT_OIDC_AUDIENCE="<OIDC-audience>"
  JOBBERGATE_AGENT_OIDC_CLIENT_ID="<OIDC-app-client-id>"
  JOBBERGATE_AGENT_OIDC_CLIENT_SECRET="<OIDC-app-client-secret>"
  ```

  NOTE: `JOBBERGATE_AGENT_SENTRY_DSN` is optional. If you do not pass it the agent understands Sentry will not be used.

  NOTE: When both `JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_PATH` and `JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_STRING` are passed, the agent will completely ignore the `JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_PATH` and will prioritize the `JOBBERGATE_AGENT_SLURMRESTD_JWT_KEY_STRING`. Beware this behaviour.

## Local usage example

1. Run app

  ```bash
  jg-run
  ```

**Note**: this command assumes you're inside a virtual environment in which the package is installed.

**NOTE**: beware you should care about having the same user name you're using to run the code in the slurmctld node. For example, if `cluster_agent` will run the `make run` command then the slurmctld node also must have a user called `cluster_agent`.
