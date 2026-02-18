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

    Copy the example configuration file and customize it:

    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

    At minimum, configure these required settings:

    ```bash
    JOBBERGATE_AGENT_BASE_API_URL="<base-api-url>"
    JOBBERGATE_AGENT_X_SLURM_USER_NAME="<sbatch-user-name>"
    JOBBERGATE_AGENT_OIDC_DOMAIN="<OIDC-domain>"
    JOBBERGATE_AGENT_OIDC_CLIENT_ID="<OIDC-app-client-id>"
    JOBBERGATE_AGENT_OIDC_CLIENT_SECRET="<OIDC-app-client-secret>"
    ```

    **Note**: `JOBBERGATE_AGENT_SENTRY_DSN` is optional. If you do not pass it the agent understands Sentry will not be used.

3. User Mapper Configuration

    The agent supports multiple user mapping strategies to map Jobbergate email addresses to local Slurm usernames:

    **Single User Mapper (Default)**

    Maps all Jobbergate users to a single Slurm user. This is the default if `SLURM_USER_MAPPER` is not specified.

    ```bash
    JOBBERGATE_AGENT_SLURM_USER_MAPPER="single-user-mapper"
    # or omit SLURM_USER_MAPPER to use this as default
    ```

    **LDAP User Mapper**

    Maps users via LDAP/Active Directory lookups. To enable LDAP mapping, configure:

    ```bash
    JOBBERGATE_AGENT_SLURM_USER_MAPPER="ldap-cached-mapper"
    JOBBERGATE_AGENT_LDAP_URI="ldap://ldap.example.com:389"
    JOBBERGATE_AGENT_LDAP_DOMAIN="example.com"
    JOBBERGATE_AGENT_LDAP_USERNAME="<ldap-service-account>"
    JOBBERGATE_AGENT_LDAP_PASSWORD="<ldap-password>"
    ```

    - `SLURM_USER_MAPPER`: Set to `ldap-cached-mapper` to enable LDAP user mapping
    - `LDAP_URI`: The URI of the LDAP server (e.g., `ldap://ldap.example.com:389` or `ldaps://ldap.example.com:636`)
    - `LDAP_DOMAIN`: The domain name used for NTLM authentication and search base construction (e.g., `example.com`)
    - `LDAP_USERNAME`: Service account username for LDAP authentication
    - `LDAP_PASSWORD`: Service account password for LDAP authentication

    The LDAP mapper caches user lookups in a local SQLite database for performance.

## Local usage example

1. Run app

    ```bash
    jg-run
    ```

    **Note**: this command assumes you're inside a virtual environment in which the package is installed.

    **Note**: beware you should care about having the same user name you're using to run the code in the slurmctld node. For example, if `cluster_agent` will run the `make run` command then the slurmctld node also must have a user called `cluster_agent`.
