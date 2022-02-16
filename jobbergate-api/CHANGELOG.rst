============
 Change Log
============

This file keeps track of all notable changes to jobbergate-api

Unreleased
----------

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
- Fixed applicaiton creation

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
