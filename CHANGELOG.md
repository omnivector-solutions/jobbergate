# Change Log

This file keeps track of all notable changes to jobbergate's components.

## Unreleased

<!-- towncrier release notes start -->

## [5.0.0a0](https://github.com/omnivector-solutions/jobbergate/releases/tag/5.0.0a0) - 2024-03-26

### Core

- Dropped support for Python 3.8 and 3.9
- Added helpers to interact with Slurm by using sbatch to submit jobs and scontrol que get information about them ([ASP-4585](https://jira.scania.com/browse/ASP-4585))

### Agent

- Dropped support for Python 3.8 and 3.9
- Replaced slurmrestd as the way the agent interacts with slurm by using sbatch to submit jobs and scontrol to get information about them ([ASP-4585](https://jira.scania.com/browse/ASP-4585))

### API

- Fixed a bug when an empty string is passed as a value for `execution_directory` on job submissions
- Modified the interface with slurm from slurmrestd to sbatch command ([ASP-4584](https://jira.scania.com/browse/ASP-4584))
  - Removed database column `JobSubmission.execution_parameters`
  - Added database column `JobSubmission.sbatch_arguments` as a list of strings

### CLI

- Fixed bug on `jobbergate_cli.subapps.applications.questions.Integer` when a default of zero could not be set properly
- Dropped support for Python 3.8 and 3.9
- Modified the interface with slurm from slurmrestd to sbatch command ([ASP-4586](https://jira.scania.com/browse/ASP-4586)):
  - Added Jobbergate-core as a project dependency to reuse key components
  - Refactored on-site submission to use the new `jobbergate-core` components
  - Replaced `execution_parameters` by `sbatch_arguments` on job submission
  - Refactored `jobbergate_cli.subapps.job_submissions.tools.create_submission` into two classes in the same module to reduce complexity in the codebase

## [4.4.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/4.4.0) - 2024-03-19

### API

- Removed SQL savepoints for auto-sessions
- Added configurable SQL logging
- Pinned aio-pika dependency to avoid issues with opentelemetry ([PENG-2111](https://app.clickup.com/t/18022949/PENG-2111))
- Downgrade FastAPI to 0.99.1 to patch issue on the file endpoints
- Added notifications via rabbitmq for job status updates ([PENG-2039](https://app.clickup.com/t/18022949/PENG-2039))

### CLI

- Removed `output_directory` from the schema `JobbergateConfig` for backward compatibility with jobbergate-legacy ([ASP-4322](https://jira.scania.com/browse/ASP-4322))
- Fixed bug on `jobbergate_cli.subapps.applications.application_helpers.get_running_jobs` when squeue finds no job ([ASP-4322](https://jira.scania.com/browse/ASP-4322))
- Fixed bug on `jobbergate application update` to pull the correct entry when the identifier is updated
- Modified the Question/Answer workflow to make it behave like jobbergate-legacy ([ASP-4332](https://jira.scania.com/browse/ASP-4332))
- Added command to render an application into a job script locally ([ASP-3326](https://jira.scania.com/browse/ASP-3326))

## [4.3.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/4.3.0) - 2024-02-14

### Agent

- Revamped job_submissions statuses and tracked more details slurm job_state ([PENG-2064](https://app.clickup.com/t/18022949/PENG-2064))
  - Renamed the finish.py module to update.py
  - Changed logic such that all active jobs have their job state updated on each pass
  - Moved all logic from the api.py module to update.py and submit.py
  - Updated schemas for revised job payloads
  - Updated and added unit tests
- Added the job property `environment` since it is required when configured to interact with slurm rest `0.0.39`
- Map job submissions with cancelled status ([ASP-4288](https://jira.scania.com/browse/ASP-4288))

### API

- Revamped job_submissions statuses and tracked more details slurm job_state ([PENG-2064](https://app.clickup.com/t/18022949/PENG-2064))
  - Added columns for slurm_job_state and slurm_job_info
  - Added mappings for slurm_job_state details (long descriptions and
    abbreviations)
  - Updated schemas for job payloads
  - Created specialized submit and reject endpoints so that agent
    doesn't need to understand job_submission statuses
  - Added a migration for the database changes including existing status mapping
  - Updated and added unit tests
- Fixed performance issue with the list endpoints dispatching additional select queries ([PENG-2059](https://app.clickup.com/t/18022949/PENG-2059))
- Added clone capability to templates and job scripts ([ASP-3335](https://jira.scania.com/browse/ASP-3335))
- Improved error handling and reporting ([ASP-4095](https://jira.scania.com/browse/ASP-4095))
- Fixed `inject_sbatch_params` when no `#SBATCH` directive was found on the file
- Added syntax validation for uploaded files (jinja2, yaml, and Python), ported from Jobbergate-API 3.6
- Map job submissions with cancelled status ([ASP-4288](https://jira.scania.com/browse/ASP-4288))

### CLI

- Revamped job_submissions statuses and tracked more details slurm job_state ([PENG-2064](https://app.clickup.com/t/18022949/PENG-2064))
  - Updated schemas for revised job payloads
  - Made slurm_job_info hidden by default on job_submissions
- Fixed JobSubmissionsResponse schema to allow for `None` values in `job_script_id`
- Reviewed how columns are sorted and colored on listing commands
- Fixed cluster_name presentation in multi-tenancy mode ([PENG-2045](https://app.clickup.com/t/18022949/PENG-2045))
- Added commands to clone templates and job scripts ([ASP-3335](https://jira.scania.com/browse/ASP-3335))
- Allow methods from `JobbergateBaseApplication` to return None for backward compatibility ([ASP-4557](https://jira.scania.com/browse/ASP-4557))
- Allow application script to dynamically overwrite job-script's name ([ASP-4558](https://jira.scania.com/browse/ASP-4558))
- Improved error handling and reporting ([ASP-4095](https://jira.scania.com/browse/ASP-4095))

### Docs

- Revamped job_submissions statuses and tracked more details slurm job_state ([PENG-2064](https://app.clickup.com/t/18022949/PENG-2064))
  - Slight docs updates for the agent app
  - Slight docs updates for the tutorial

## [4.2.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/4.2.0) - 2024-01-08

### Core

- Added support for Python 3.12

### Agent

- Capture request errors with Slurm API in Sentry notifications ([PENG-2000](https://app.clickup.com/t/18022949/PENG-2000))
- Capture request errors with Jobbergate API in Sentry notifications ([PENG-2000](https://app.clickup.com/t/18022949/PENG-2000))
- Added support for Python 3.12
- Added setting to specify if the job script files should be written to the submit directory ([ASP-4245](https://jira.scania.com/browse/ASP-4245))
- Added setting to control the timeout on `httpx` requests

### API

- Added constraints to prevent long strings from being inserted into the database ([ASP-4113](https://jira.scania.com/browse/ASP-4113))
- Added constraints to prevent negative id numbers from being inserted into the database ([ASP-4113](https://jira.scania.com/browse/ASP-4113))
- Added constraints to limit the size on the uploaded files ([ASP-4113](https://jira.scania.com/browse/ASP-4113))
- Added support for on-site job submissions ([ASP-4238](https://jira.scania.com/browse/ASP-4238))
- Moved database session management into a dedicated context manager and removed test-aware logic
- Modified testing harnesses to override session management context manager and fail if test session is not used

### CLI

- Added instructions to checkbox questions ([ASP-4042](https://jira.scania.com/browse/ASP-4042))
- Added support for Python 3.12
- Fixed the setting `CACHE_DIR` to expand the user home directory, allowing more flexibility on the path ([ASP-4053](https://jira.scania.com/browse/ASP-4053))
- Fixed the question `BooleanList` to allow subquestion to have the same name ([ASP-4228](https://jira.scania.com/browse/ASP-4228))
- Added pagination support for `list` commands ([ASP-3966](https://jira.scania.com/browse/ASP-3966))
- Added support for on-site job submissions using the `sbatch` command ([ASP-4238](https://jira.scania.com/browse/ASP-4238))
- Added setting to control the timeout on `httpx` requests ([ASP-3946](https://jira.scania.com/browse/ASP-3946))
- Added a new config to change the way job-script files are named to `<job-script-name>.job`, following behavior from jobbergate-legacy ([ASP-4069](https://jira.scania.com/browse/ASP-4069))
- Added ability to open the login url on a browser or copy it to the user's clipboard ([ASP-4053](https://jira.scania.com/browse/ASP-4053))
- Added --cluster-name, --execution-directory and --download parameters to `create-job-script` command on submit mode
- Changed application-id, job-script-id and job-submission-id to have alias when displaying the id on the CLI
- Added a `create` for Job Scripts to create without Template (former `create` renamed to `render`)
- Fixed help information for id on `get-job-script`, `download-job-script`, and `get-job-submission` commands
- Added short arguments in many commands for backward compatibility
- Added username and password as arguments, they are ignored if provided aiming to keep compatibility with legacy aliases
- Added support to select applications by identifier in update and delete commands
- Added show-files command to compatibility mode
- Added support to select all and deselect all options in checkboxes using Ctrl+A and Ctrl+R as shortcuts
- Added an alternative way to present to login url on narrow terminals

### Docs

- Added new page describing the support for on-site job submissions ([ASP-4238](https://jira.scania.com/browse/ASP-4238))

## [4.1.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/4.1.0) - 2023-11-07

### API

- Changed internals to avoid committing to the database when a GET request is made
- Added extra settings to allow profiling and tracing on sentry
- Removed db-start from dev-tools
- Added `container` on job properties for submissions, new in Slurm REST 0.0.38
- Made `runtime_config` optional when uploading a workflow file
- Exposed database connection pool settings through the app configuration

### Docs

- Converted to Markdown and built with mkdocs-material

## [4.0.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/4.0.0) - 2023-09-14

### Agent

- Started the project

### API

- Modified the API to address the new data model on Jobbergate
- Added functionality to make make the signal job property on job submissions backward compatible with legacy applications
- Add backward compatibility for organization_id on the identity payload
- Build: Include dev dependencies in the docker image
- Added `pendulum` to the requirements
- Modified internal timestamps to standardize the use of UTC

### CLI

- Modified internal details to address the new data model on Jobbergate API
- Drop support for Python 3.6
- Fixed refresh token not being updated on cache after token refresh

### Docs

- Keep synchronized with jobbergate-cli and jobbergate-api

## [3.4.3](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.4.3) - 2023-01-30

### API

- Patched the sbatch param parser to support special characters

## [3.4.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.4.2) - 2023-01-25

### API

- Fixed put endpoints on job-submission to return the correct data

## [3.4.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.4.1) - 2023-01-16

### API

- Fix a compatibility issue on JobbergateConfig by removing the leading "templates/" on the path for template files
- Fix some compatibility issues on the JobProperties schema for job submissions
- Fix the field `execution_parameters` that is optional at job submission creations

## [3.4.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.4.0) - 2023-01-03

### API

- Move SBATCH params to Job Script submission
- Added field `from_application_id` to filter job scripts on the list endpoint
- Added field `from_job_script_id` to filter job submissions on the list endpoint

### CLI

- Added support for `execution_parameters` in job submission at the CLI
- Added new command to download application files to the current working directory
- Added new command to download job script files to the current working directory
- Added new option to create-job-submission to allow download job script files to current working directory
- Added parameters `from_application_id` to filter job scripts on the list command
- Added parameters `from_job_script_id` to filter job submissions on the list command
- Fixed missing user defined fields when loading jobbergate.yaml

## [3.3.4](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.3.4) - 2022-12-05

### API

- Added version metadata to the API

### CLI

- Make the name optional when creating a new job script on the CLI
- Fixed `report_message` not showing on the detailed view of a job submissions

### Docs

- Massive update of the Jobbergate documentation
- Inclusion of Motorbike example and walk-through

## [3.3.3](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.3.3) - 2022-10-17

### API

- Added logic to ignore leading templates/ path in default template

### CLI

- Fixed issue with optional output directory

## [3.3.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.3.2) - 2022-10-13

### API

- Fixed a bug at the file manager where the search for objects at s3 was not restricted to a single folder
- Changed the jinja2 syntax validation in order to make it more flexible with regard to the data expected in the template

### CLI

- Fixed `output_directory` on JobbergateConfig making it optional, as it is at the API level
- Fixed issues with `CRLF` end of lines when uploading application files

## [3.3.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.3.1) - 2022-10-10

### CLI

- Fixed refresh (invalid paths for refresh endpoints)
- Added DEFAULT_CLUSTER_NAME (fast-mode broken due to invalid cluster)

## [3.3.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.3.0) - 2022-10-04

### API

- Added logic for supporting files on job-scripts.
- Changed dev-tools to use alembic functions instead of subprocess calls
- Changed default log level to DEBUG instead of INFO
- Added ARMASEC_USE_HTTPS setting to allow non-https OIDC providers
- Added better logging and reporting for pydantic validation errors
- Added job_submissions.status as a sortable field

### CLI

- Added error details to configuration error report
- Added ``OIDC_USE_HTTPS`` setting to allow non-https OIDC hosts
- Removed cluster validation from job-submission due to reliance on external cluster registry
- Added a `show-files` subcommand to `job-scripts` to show job script files
- Modified cache dir and dotenv path in order to avoid conflicts when installed alongside legacy jobbergate

## [3.2.4](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.4) - 2022-09-12

### API

- Patch the supporting files on job-scripts.
- Refactor application file management in a class, making it modular and reusable.
- Fix a bug when writing application files to S3 and add tests to cover the issue.
- Fix API was not sending job-script files to the agent.
- Refactor Jobbergate application file management.

### CLI

- Refactor the logic to upload application files to the API.
- Remove file validation from the CLI.
- Remove compression of the upload files into tarballs.

## [3.2.3](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.3) - 2022-08-01

### API

- Patch cli authentication configurations.
- Added support to release on PyPI.

### CLI

- Patch cli authentication configurations.
- Added support to release on PyPI.

## [3.2.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.2) - 2022-07-28

### API

- Fixed a bug with option email in the token payload.

## [3.2.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.1) - 2022-07-12

### API

- Job scripts were moved from a database column to files at S3.
- Added email notification to Jobbergate.
- More debug log messages were added to the API.
- Implemented support for multi-domain authentication.

## [3.2.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.1) - 2022-06-24

## [3.2.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.2.0) - 2022-06-24

### API

- Adjusted variables and data structures for keycloak migration

### CLI

- Set ``environment`` variable for Sentry based on settings parameter.
- Adjusted variables and data structures for keycloak migration

## [3.1.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.1.1) - 2022-06-01

### API

- Removed AWS settings. Boto3 supports these env variables natively.

### CLI

- Added warning and handling for empty access tokens in the cache.

## [3.1.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.1.0) - 2022-04-20

### API

- Added execution_directory to job submissions

### CLI

- Added execution_directory to job submissions
- Added checks for empty cached token files

## [3.0.4](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.0.4) - 2022-04-11

### API

- Made supplying param_dict optional in job-scripts create (will use app defaults)
- Included some example scripts for working with API directly.

### CLI

- Made supplying param_dict optional in API job-scripts create.
- Included some example scripts for working with API directly.

## [3.0.3](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.0.3) - 2022-04-08

### API

- Restored jobberappslib in jobbergate CLI

### CLI

- Restored jobberappslib (with deprecation warnings as appropriate)

## [3.0.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.0.2) - 2022-04-08

### API

- Fixed compatibility issues with python 3.6 in CLI

### CLI

- Fixed compatibility issues with python 3.6

## [3.0.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.0.1) - 2022-04-08

### API

- Revised production dockerfile to not use gunicorn
- Updated some dependencies
- Fixed publish github action

### CLI

- Fixed publish github action

## [3.0.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/3.0.0) - 2022-04-04

### API

- Removed owner_email from create schemas (this comes from token now)
- Changed status codes for update routes to 200
- Added `migrate` and `upgrade` commands to dev-tools
- Added endpoints for agent to pull pending jobs and update active jobs
- Moved dev-tools into their own separate sub-package (not included in builds)
- Added github action for publishing images to ECR

### CLI

- Complete re-write of the Jobbergate CLI
- Used typer to implement the application
- Styled user output with Rich formatting
- Broke the code up into modules and functions for easier maintenance and reading
- Refactored the question asking system in applications
- Added over 100 unit tests

## [2.2.9](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.9) - 2022-02-16

### API

- Added AUTH0_LOGIN_DOMAIN setting in CLI
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN in CLI

### CLI

- Added AUTH0_LOGIN_DOMAIN setting
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN

## [2.2.8](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.8) - 2022-02-15

### API

- Fixed job submission data format for creation POST request in CLI

### CLI

- Fixed job submission data format for creation POST request

## [2.2.7](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.7) - 2022-02-15

### API

- Applied fix for requests and added more debug logging in CLI

### CLI

- Applied fix for requests and added more debug logging

## [2.2.6](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.6) - 2022-02-14

### API

- Added search and sort capability to the list endpoints

### CLI

- Added search and sort capability to the list endpoints to the API

## [2.2.5](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.5) - 2022-02-14

### API

- Removed job_script_data_as_string from create parameters for job_script create

### CLI

- Removed job_script_data_as_string from create parameters for job_script create in API

## [2.2.4](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.4) - 2022-02-14

### API

- Fixed urls in the CLI again

### CLI

- Fixed urls in the CLI again

## [2.2.3](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.3) - 2022-02-14

### API

- Improved error messages for users and captured error info in CLI

### CLI

- Improved error messages for users and captured error info

## [2.2.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.2) - 2022-02-07

### API

- Fixed application creation

### CLI

- Fixed applicaiton creation

## [2.2.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.1) - 2022-02-03

### API

- Bumping version to sync with the CLI

### CLI

- Fixed issue with SENTRY_DSN shadowing API initialization

## [2.2.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.2.0) - 2022-02-03

### API

- Removed trailing slashes from api endpoints

### CLI

- Removed trailing slashes from api endpoints

## [2.1.2](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.1.2) - 2022-02-02

### API

- Revised permissions to use a view/edit model for each data model

- Added parameter to filter job_submissions by slurm_job_id

### CLI

- Revised login workflow to use client-credentials auth workflow
- Fixed IDENTITY_CLAIMS_KEY to be overrideable by environment

## [2.1.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.1.1) - 2022-01-13

### API

- Refactored the Dockerfile

## [2.1.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.1.0) - 2021-12-22

### API

- Added graceful handling of delete failures due to FK constraints

- Added Alembic support
- Added application_identifier to response payload
- Added pagination support back in

## [2.0.1](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.0.1) - 2021-12-10

### API

- Removed CORS origins parameter from settings and set all origins as the allowed ones

## [2.0.0](https://github.com/omnivector-solutions/jobbergate/releases/tag/2.0.0) - 2021-12-08

### API

- Added support for auth via Armasec & Auth0

- Added unit tests
- Migrated model definitions from legacy `jobbergate-api`
- Migrated endpoint definitions from legacy `jobbergate-api`
- Created FastAPI application and added basic routes
- Added support for database migrations via Alembic
- Added Makefile with targets to install, test, migrate, run, and clean
- Added CI workflow for github action to test PRs
- Added basic documentation in README
- Created project with poetry for dependency and project management
- Renamed module folder from jobbergateapi2 to jobbergate_api
- Fixed ownership mapping for entities to use email instead of id

### CLI

- Migrated from legacy jobbegate-cli project
