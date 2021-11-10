============
 Change Log
============

This file keeps track of all notable changes to jobbergate-cli

Unreleased
----------

1.1.1 -- 2021-11-08
-------------------
- Removed leftover debug exception to fix ``list-applications`` command

1.1.0 -- 2021-11-05
-------------------
- Fixed bug for getting job_script name from params
- Added Sentry integration
- Added logging in user space and ability to upload logs to S3
- Added release scripts
- Converted to using poetry for dependencies and publishing
- Added targets in makefile
