# Change Log

This file keeps track of all notable changes to jobbergate-api

## Unreleased
- Bumped dependencies (FastAPI and fastapi-pagination)

## 5.3.0 -- 2024-09-09

- Fixed issue preventing the creation of a job script from an empty template file
- Enhance logging for file storage operations
- Implemented an endpoint to fetch a cluster status by its client id [[PENG-2348](https://sharing.clickup.com/t/h/c/18022949/PENG-2348/QWZFBKV72ZNL293)]
- Remove the audience setting [[PENG-2230](https://sharing.clickup.com/t/h/c/18022949/PENG-2230/O40JANAF6KCBE9R)]
- Added `jobbergate:maintainer` role [[PENG-2323](https://app.clickup.com/t/18022949/PENG-2323)]
    - `jobbergate:maintainer` acts as previous `jobbergate:admin` role, allowing users to update/delete entities owned by others
    - `jobbergate:admin` now grants access to all endpoints besides the `jobbergate:maintainer` role

## 5.2.0 -- 2024-07-01

- Fixed issue when retrieving large files on get routes after upgrading to FastAPI 0.111
- Change pydantic.BaseSettings config to use `extra=ignore`
- Migrated to Pydantic version 2 [PENG-2277]
  - Upgraded pydantic to 2.7
  - Upgraded fastapi to 0.111
  - Upgraded armasec to 2.0.1
  - Added pydantic-settings 2.2.1
- Updated linter and format checker to use ruff
- Improve performance on Automatically clean up unused job scripts [ASP-5186]
- Enabled template and job-script files to be renamed on upsert routes [PENG-2070]
- Added a response model for PUT on `/job-scripts/{id}/upload/{file_type}`
- Expanded permission sets from view/edit to create/read/update/delete
- Added admin role to allow key users to update/delete entities owned by others [ASP-4989]

## 5.1.0 -- 2024-04-19

- Added cluster statuses table and endpoints to monitor if the agents are pinging the API in the expected time interval [ASP-4600]

## 5.0.0 -- 2024-04-18

- Added logic to coerce empty `identifier` on job script templates to a `None` value [PENG-2152]
- Added logic disallow empty `name` on job script templates [PENG-2152]
- Fixed a bug when an empty string is passed as a value for `execution_directory` on job submissions
- Modified the interface with slurm from slurmrestd to sbatch command [ASP-4584]
  - Removed database column `JobSubmission.execution_parameters`
  - Added database column `JobSubmission.sbatch_arguments` as a list of strings

## 4.4.0 -- 2024-03-19

- Removed SQL savepoints for auto-sessions
- Added configurable SQL logging
- Pinned aio-pika dependency to avoid issues with opentelemetry [PENG-2111]
- Downgrade FastAPI to 0.99.1 to patch issue on the file endpoints
- Added notifications via rabbitmq for job status updates [PENG-2039]

## 4.3.0 -- 2024-02-14

- Revamped job_submissions statuses and tracked more details slurm job_state [PENG-2064]
  - Added columns for slurm_job_state and slurm_job_info
  - Added mappings for slurm_job_state details (long descriptions and
    abbreviations)
  - Updated schemas for job payloads
  - Created specialized submit and reject endpoints so that agent
    doesn't need to understand job_submission statuses
  - Added a migration for the database changes including existing status mapping
  - Updated and added unit tests
- Fixed performance issue with the list endpoints dispatching additional select queries [PENG-2059]
- Added clone capability to templates and job scripts [ASP-3335]
- Improved error handling and reporting [ASP-4095]
- Fixed `inject_sbatch_params` when no `#SBATCH` directive was found on the file
- Added syntax validation for uploaded files (jinja2, yaml, and Python), ported from Jobbergate-API 3.6
- Map job submissions with cancelled status [ASP-4288]

## 4.2.0 -- 2024-01-08

- Added constraints to prevent long strings from being inserted into the database [ASP-4113]
- Added constraints to prevent negative id numbers from being inserted into the database [ASP-4113]
- Added constraints to limit the size on the uploaded files [ASP-4113]
- Added support for on-site job submissions [ASP-4238]
- Moved database session management into a dedicated context manager and removed test-aware logic
- Modified testing harnesses to override session management context manager and fail if test session is not used

## 4.1.0 -- 2023-11-07

- Changed internals to avoid committing to the database when a GET request is made
- Added extra settings to allow profiling and tracing on sentry
- Removed db-start from dev-tools
- Added `container` on job properties for submissions, new in Slurm REST 0.0.38
- Made `runtime_config` optional when uploading a workflow file
- Exposed database connection pool settings through the app configuration

## 4.0.0 -- 2023-09-14

- Modified the API to address the new data model on Jobbergate
- Added functionality to make make the signal job property on job submissions backward compatible with legacy applications
- Add backward compatibility for organization_id on the identity payload
- Build: Include dev dependencies in the docker image
- Added `pendulum` to the requirements
- Modified internal timestamps to standardize the use of UTC

## 3.4.3 -- 2023-01-30

- Patched the sbatch param parser to support special characters

## 3.4.2 -- 2023-01-25

- Fixed put endpoints on job-submission to return the correct data

## 3.4.1 -- 2023-01-16

- Fix a compatibility issue on JobbergateConfig by removing the leading "templates/" on the path for template files
- Fix some compatibility issues on the JobProperties schema for job submissions
- Fix the field `execution_parameters` that is optional at job submission creations

## 3.4.0 -- 2023-01-03

- Move SBATCH params to Job Script submission
- Added field `from_application_id` to filter job scripts on the list endpoint
- Added field `from_job_script_id` to filter job submissions on the list endpoint

## 3.3.4 -- 2022-12-05

- Added version metadata to the API

## 3.3.3 -- 2022-10-17

- Added logic to ignore leading templates/ path in default template

## 3.3.2 -- 2022-10-13

- Fixed a bug at the file manager where the search for objects at s3 was not restricted to a single folder
- Changed the jinja2 syntax validation in order to make it more flexible with regard to the data expected in the template

## 3.3.1 -- 2022-10-10

- Keep synchronized with jobbergate-cli

## 3.3.0 -- 2022-10-04

- Added logic for supporting files on job-scripts.
- Changed dev-tools to use alembic functions instead of subprocess calls
- Changed default log level to DEBUG instead of INFO
- Added ARMASEC_USE_HTTPS setting to allow non-https OIDC providers
- Added better logging and reporting for pydantic validation errors
- Added job_submissions.status as a sortable field

## 3.2.4 -- 2022-09-12

- Patch the supporting files on job-scripts.
- Refactor application file management in a class, making it modular and reusable.
- Fix a bug when writing application files to S3 and add tests to cover the issue.
- Fix API was not sending job-script files to the agent.
- Refactor Jobbergate application file management.

## 3.2.3 -- 2022-08-01

- Patch cli authentication configurations.
- Added support to release on PyPI.

## 3.2.2 -- 2022-07-28

- Fixed a bug with option email in the token payload.

## 3.2.1 -- 2022-07-12

- Job scripts were moved from a database column to files at S3.
- Added email notification to Jobbergate.
- More debug log messages were added to the API.
- Implemented support for multi-domain authentication.

## 3.2.0 -- 2022-06-24

- Adjusted variables and data structures for keycloak migration

## 3.1.1 -- 2022-06-01

- Removed AWS settings. Boto3 supports these env variables natively.

## 3.1.0 -- 2022-04-20

- Added execution_directory to job submissions

## 3.0.4 -- 2022-04-11

- Made supplying param_dict optional in job-scripts create (will use app defaults)
- Included some example scripts for working with API directly.

## 3.0.3 -- 2022-04-08

- Restored jobberappslib in jobbergate CLI

## 3.0.2 -- 2022-04-08

- Fixed compatibility issues with python 3.6 in CLI

## 3.0.1 -- 2022-04-08

- Revised production dockerfile to not use gunicorn
- Updated some dependencies
- Fixed publish github action

## 3.0.0 -- 2022-04-04

- Removed owner_email from create schemas (this comes from token now)
- Changed status codes for update routes to 200
- Added `migrate` and `upgrade` commands to dev-tools
- Added endpoints for agent to pull pending jobs and update active jobs
- Moved dev-tools into their own separate sub-package (not included in builds)
- Added github action for publishing images to ECR

## 2.2.9 -- 2022-02-16

- Added AUTH0_LOGIN_DOMAIN setting in CLI
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN in CLI

## 2.2.8 -- 2022-02-15

- Fixed job submission data format for creation POST request in CLI

## 2.2.7 -- 2022-02-15

- Applied fix for requests and added more debug logging in CLI

## 2.2.6 -- 2022-02-14

- Added search and sort capability to the list endpoints

## 2.2.5 -- 2022-02-14

- Removed job_script_data_as_string from create parameters for job_script create

## 2.2.4 -- 2022-02-14

- Fixed urls in the CLI again

## 2.2.3 -- 2022-02-14

- Improved error messages for users and captured error info in CLI

## 2.2.2 -- 2022-02-07

- Fixed application creation

## 2.2.1 -- 2022-02-03

- Bumping version to sync with the CLI

## 2.2.0 -- 2022-02-03

- Removed trailing slashes from api endpoints

## 2.1.2 -- 2022-02-02

- Revised permissions to use a view/edit model for each data model

- Added parameter to filter job_submissions by slurm_job_id

## 2.1.1 -- 2022-01-13

- Refactored the Dockerfile

## 2.1.0 -- 2021-12-22

- Added graceful handling of delete failures due to FK constraints

- Added Alembic support
- Added application_identifier to response payload
- Added pagination support back in

## 2.0.1 -- 2021-12-10

- Removed CORS origins parameter from settings and set all origins as the allowed ones

## 2.0.0 -- 2021-12-08

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
