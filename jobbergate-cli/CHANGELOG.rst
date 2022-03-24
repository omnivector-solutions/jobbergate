============
 Change Log
============

This file keeps track of all notable changes to jobbergate-cli

Unreleased
----------
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
