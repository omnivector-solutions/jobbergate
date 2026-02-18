# Jobbergate-agent

## Install the package

To install the package from Pypi simply run `pip install jobbergate-agent`.

## Setup parameters

1. Setup dependencies

    Dependencies and environment are managed in the project by [uv](https://docs.astral.sh/uv/). To initiate the development environment run:

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

3. LDAP User Mapper Configuration (Optional)

    If using the LDAP user mapper plugin, configure the following environment variables:

    ```bash
    JOBBERGATE_AGENT_LDAP_URI="ldap://ldap.example.com:389"
    JOBBERGATE_AGENT_LDAP_DOMAIN="example.com"
    JOBBERGATE_AGENT_LDAP_USERNAME="<ldap-username>"
    JOBBERGATE_AGENT_LDAP_PASSWORD="<ldap-password>"
    ```

    - `LDAP_URI`: The URI of the LDAP server (e.g., `ldap://ldap.example.com:389` or `ldaps://ldap.example.com:636`)
    - `LDAP_DOMAIN`: The domain name used for NTLM authentication and search base construction (e.g., `example.com`)
    - `LDAP_USERNAME`: The username for LDAP authentication
    - `LDAP_PASSWORD`: The password for LDAP authentication

## Local usage example

1. Run app

    ```bash
    jg-run
    ```

    **Note**: this command assumes you're inside a virtual environment in which the package is installed.

    **Note**: beware you should care about having the same user name you're using to run the code in the slurmctld node. For example, if `cluster_agent` will run the `make run` command then the slurmctld node also must have a user called `cluster_agent`.
