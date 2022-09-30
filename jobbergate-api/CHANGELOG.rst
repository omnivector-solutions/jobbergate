============
 Change Log
============

This file keeps track of all notable changes to jobbergate-api

Unreleased
----------

3.3.0-alpha.0 -- 2022-09-30
---------------------------
- Added logic for supporting files on job-scripts.
- Changed dev-tools to use alembic functions instead of subprocess calls
- Changed default log level to DEBUG instead of INFO
- Added ARMASEC_USE_HTTPS setting to allow non-https OIDC providers
- Added better logging and reporting for pydantic validation errors
- Fixed sorting in job_submissiosn.status

3.2.5-alpha.0 -- 2022-09-15
---------------------------
- Added job_submissions.status as a sortable field

3.2.4 -- 2022-09-12
-------------------
- Patch the supporting files on job-scripts.
- Refactor application file management in a class, making it modular and reusable.
- Fix a bug when writing application files to S3 and add tests to cover the issue.
- Fix API was not sending job-script files to the agent.
- Refactor Jobbergate application file management.

3.2.3 -- 2022-08-01
-------------------
- Patch cli authentication configurations.
- Added support to release on PyPI.

3.2.2 -- 2022-07-28
-------------------
- Fixed a bug with option email in the token payload.

3.2.1 -- 2022-07-12
-------------------
- Job scripts were moved from a database column to files at S3.
- Added email notification to Jobbergate.
- More debug log messages were added to the API.
- Implemented support for multi-domain authentication.

3.2.0 -- 2022-06-24
-------------------
- Adjusted variables and data structures for keycloak migration

3.1.1 -- 2022-06-01
-------------------
- Removed AWS settings. Boto3 supports these env variables natively.

3.1.0 -- 2022-04-20
-------------------
- Added execution_directory to job submissions

3.0.4 -- 2022-04-11
-------------------
- Made supplying param_dict optional in job-scripts create (will use app defaults)
- Included some example scripts for working with API directly.

3.0.3 -- 2022-04-08
-------------------
- Restored jobberappslib in jobbergate CLI

3.0.2 -- 2022-04-08
-------------------
- Fixed compatibility issues with python 3.6 in CLI

3.0.1 -- 2022-04-08
-------------------
- Revised production dockerfile to not use gunicorn
- Updated some dependencies
- Fixed publish github action

3.0.0 -- 2022-04-04
-------------------
- Removed owner_email from create schemas (this comes from token now)
- Changed status codes for update routes to 200
- Added ``migrate`` and ``upgrade`` commands to dev-tools
- Added endpoints for agent to pull pending jobs and update active jobs
- Moved dev-tools into their own separate sub-package (not included in builds)
- Added github action for publishing images to ECR

2.2.9 -- 2022-02-16
-------------------
- Added AUTH0_LOGIN_DOMAIN setting in CLI
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN in CLI

2.2.8 -- 2022-02-15
-------------------
- Fixed job submission data format for creation POST request in CLI

2.2.7 -- 2022-02-15
-------------------
- Applied fix for requests and added more debug logging in CLI

2.2.6 -- 2022-02-14
-------------------
- Added search and sort capability to the list endpoints

2.2.5 -- 2022-02-14
-------------------
- Removed job_script_data_as_string from create parameters for job_script create

2.2.4 -- 2022-02-14
-------------------
- Fixed urls in the CLI again

2.2.3 -- 2022-02-14
-------------------
- Improved error messages for users and captured error info in CLI

2.2.2 -- 2022-02-07
-------------------
- Fixed application creation

2.2.1 -- 2022-02-03
-------------------
- Bumping version to sync with the CLI

2.2.0 -- 2022-02-03
-------------------
- Removed trailing slashes from api endpoints

2.1.2 -- 2022-02-02
-------------------
* Revised permissions to use a view/edit model for each data model
* Added parameter to filter job_submissions by slurm_job_id

2.1.1 -- 2022-01-13
-------------------
* Refactored the Dockerfile

2.1.0 -- 2021-12-22
-------------------
* Added graceful handling of delete failures due to FK constraints
* Added Alembic support
* Added application_identifier to response payload
* Added pagination support back in

2.0.1 -- 2021-12-10
-------------------
* Removed CORS origins parameter from settings and set all origins as the allowed ones

2.0.0 -- 2021-12-08
-------------------
* Added support for auth via Armasec & Auth0
* Added unit tests
* Migrated model definitions from legacy ``jobbergate-api``
* Migrated endpoint definitions from legacy ``jobbergate-api``
* Created FastAPI application and added basic routes
* Added support for database migrations via Alembic
* Added Makefile with targets to install, test, migrate, run, and clean
* Added CI workflow for github action to test PRs
* Added basic documentation in README
* Created project with poetry for dependency and project management
* Renamed module folder from jobbergateapi2 to jobbergate_api
* Fixed ownership mapping for entities to use email instead of id
