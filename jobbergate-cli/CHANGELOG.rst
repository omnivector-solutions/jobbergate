============
 Change Log
============

This file keeps track of all notable changes to jobbergate-cli

Unreleased
----------
- Added error details to configuration error report
- Added ``OIDC_USE_HTTPS`` setting to allow non-https OIDC hosts
- Removed cluster validation from job-submission due to reliance on external cluster registry

3.2.5-alpha.0 -- 2022-09-15
---------------------------
- Keep version in sync with the API.

3.2.4 -- 2022-09-12
-------------------
- Refactor the logic to upload application files to the API.
- Remove file validation from the CLI.
- Remove compression of the upload files into tarballs.

3.2.3 -- 2022-08-01
-------------------
- Patch cli authentication configurations.
- Added support to release on PyPI.

3.2.2 -- 2022-07-28
-------------------
- Keep version in sync with the API.

3.2.1 -- 2022-06-24
-------------------
- Keep version in sync with the API.

3.2.0 -- 2022-06-24
-------------------
- Set ``environment`` variable for Sentry based on settings parameter.
- Adjusted variables and data structures for keycloak migration

3.1.1 -- 2022-06-01
-------------------
- Added warning and handling for empty access tokens in the cache.

3.1.0 -- 2022-04-20
-------------------
- Added execution_directory to job submissions
- Added checks for empty cached token files

3.0.4 -- 2022-04-11
-------------------
- Made supplying param_dict optional in API job-scripts create.
- Included some example scripts for working with API directly.

3.0.3 -- 2022-04-08
-------------------
- Restored jobberappslib (with deprecation warnings as appropriate)

3.0.2 -- 2022-04-08
-------------------
- Fixed compatiblity issues with python 3.6

3.0.1 -- 2022-04-08
-------------------
- Fixed publish github action

3.0.0 -- 2022-04-04
-------------------
- Complete re-write of the Jobbergate CLI
- Used typer to implement the application
- Styled user output with Rich formatting
- Broke the code up into modules and functions for easier maintenance and reading
- Refactored the question asking system in applications
- Added over 100 unit tests

2.2.9 -- 2022-02-16
-------------------
- Added AUTH0_LOGIN_DOMAIN setting
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN

2.2.8 -- 2022-02-15
-------------------
- Fixed job submission data format for creation POST request

2.2.7 -- 2022-02-15
-------------------
- Applied fix for requests and added more debug logging

2.2.6 -- 2022-02-14
-------------------
- Added search and sort capability to the list endpoints to the API

2.2.5 -- 2022-02-14
-------------------
- Removed job_script_data_as_string from create parameters for job_script create in API

2.2.4 -- 2022-02-14
-------------------
- Fixed urls in the CLI again

2.2.3 -- 2022-02-14
-------------------
- Improved error messages for users and captured error info


2.2.2 -- 2022-02-07
-------------------
- Fixed applicaiton creation

2.2.1 -- 2022-02-03
-------------------
- Fixed issue with SENTRY_DSN shadowing API initialization

2.2.0 -- 2022-02-03
-------------------
- Removed trailing slashes from api endpoints

2.1.2 -- 2022-02-02
-------------------
- Revised login workflow to use client-credentials auth workflow
- Fixed IDENTITY_CLAIMS_KEY to be overrideable by environment

2.0.0 -- 2021-12-08
-------------------
- Migrated from legacy jobbegate-cli project
