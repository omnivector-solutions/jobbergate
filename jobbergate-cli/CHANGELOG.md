# Change Log

This file keeps track of all notable changes to jobbergate-cli

## Unreleased


## 5.2.0a3 -- 2024-06-26
- Migrated to Pydantic version 2 [PENG-2279]
  - Upgraded pydantic to 2.7
  - Upgraded mypy to 1.10.0
  - Added pydantic-settings 2.3.3
- Fixed parameter `--sort-order` on the listing commands
- Updated linter and format checker to use ruff
- Added a quick start guide to be displayed when the user runs the command with no arguments and after login
- Renamed command `jobbergate job-scripts create` to `jobbergate job-scripts create-stand-alone`
- Renamed command `jobbergate job-scripts render` to `jobbergate job-scripts create`
- Renamed command `jobbergate job-scripts render-locally` to `jobbergate job-scripts create-locally`
- Fixed `ApplicationRuntime` filling supporting files when they are already set by the application as an empty list

## 5.2.0a2 -- 2024-05-31

## 5.2.0a1 -- 2024-05-24

- Hided less used commands on the cli when backward compatibility mode is enabled [ASP-5192]
- Added the subcommands `applications`, `job-scripts`, and `job-submissions` to backward compatibility mode
- Marked backward compatible commands as deprecated and indicated the new alternative

## 5.2.0a0 -- 2024-04-29

## 5.1.0 -- 2024-04-19

- Keep version in sync with the API.

## 5.0.0 -- 2024-04-18

- Fixed bug on `jobbergate_cli.subapps.applications.questions.Integer` when a default of zero could not be set properly
- Dropped support for Python 3.8 and 3.9
- Modified the interface with slurm from slurmrestd to sbatch command [ASP-4586]:
  - Added Jobbergate-core as a project dependency to reuse key components
  - Refactored on-site submission to use the new `jobbergate-core` components
  - Replaced `execution_parameters` by `sbatch_arguments` on job submission
  - Refactored `jobbergate_cli.subapps.job_submissions.tools.create_submission` into two classes in the same module to reduce complexity in the codebase

## 4.4.0 -- 2024-03-19

- Removed `output_directory` from the schema `JobbergateConfig` for backward compatibility with jobbergate-legacy [ASP-4322]
- Fixed bug on `jobbergate_cli.subapps.applications.application_helpers.get_running_jobs` when squeue finds no job [ASP-4322]
- Fixed bug on `jobbergate application update` to pull the correct entry when the identifier is updated
- Modified the Question/Answer workflow to make it behave like jobbergate-legacy [ASP-4332]
- Added command to render an application into a job script locally [ASP-3326]

## 4.3.0 -- 2024-02-14

- Revamped job_submissions statuses and tracked more details slurm job_state [PENG-2064]
  - Updated schemas for revised job payloads
  - Made slurm_job_info hidden by default on job_submissions
- Fixed JobSubmissionsResponse schema to allow for `None` values in `job_script_id`
- Reviewed how columns are sorted and colored on listing commands
- Fixed cluster_name presentation in multi-tenancy mode [PENG-2045]
- Added commands to clone templates and job scripts [ASP-3335]
- Allow methods from `JobbergateBaseApplication` to return None for backward compatibility [ASP-4557]
- Allow application script to dynamically overwrite job-script's name [ASP-4558]
- Improved error handling and reporting [ASP-4095]

## 4.2.0 -- 2024-01-08

- Added instructions to checkbox questions [ASP-4042]
- Added support for Python 3.12
- Fixed the setting `CACHE_DIR` to expand the user home directory, allowing more flexibility on the path [ASP-4053]
- Fixed the question `BooleanList` to allow subquestion to have the same name [ASP-4228]
- Added pagination support for `list` commands [ASP-3966]
- Added support for on-site job submissions using the `sbatch` command [ASP-4238]
- Added setting to control the timeout on `httpx` requests [ASP-3946]
- Added a new config to change the way job-script files are named to `<job-script-name>.job`, following behavior from jobbergate-legacy [ASP-4069]
- Added ability to open the login url on a browser or copy it to the user's clipboard [ASP-4053]
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

## 4.0.0 -- 2023-09-14

- Modified internal details to address the new data model on Jobbergate API
- Drop support for Python 3.6
- Fixed refresh token not being updated on cache after token refresh

## 3.4.3 -- 2023-01-30

- Keep version in sync with the API.

## 3.4.2 -- 2023-01-25

- Keep version in sync with the API.

## 3.4.1 -- 2023-01-16

- Keep version in sync with the API.

## 3.4.0 -- 2023-01-03

- Added support for `execution_parameters` in job submission at the CLI
- Added new command to download application files to the current working directory
- Added new command to download job script files to the current working directory
- Added new option to create-job-submission to allow download job script files to current working directory
- Added parameters `from_application_id` to filter job scripts on the list command
- Added parameters `from_job_script_id` to filter job submissions on the list command
- Fixed missing user defined fields when loading jobbergate.yaml

## 3.3.4 -- 2022-12-05

- Make the name optional when creating a new job script on the CLI
- Fixed `report_message` not showing on the detailed view of a job submissions

## 3.3.3 -- 2022-10-17

- Fixed issue with optional output directory

## 3.3.2 -- 2022-10-13

- Fixed `output_directory` on JobbergateConfig making it optional, as it is at the API level
- Fixed issues with `CRLF` end of lines when uploading application files

## 3.3.1 -- 2022-10-10

- Fixed refresh (invalid paths for refresh endpoints)
- Added DEFAULT_CLUSTER_NAME (fast-mode broken due to invalid cluster)

## 3.3.0 -- 2022-10-04

- Added error details to configuration error report
- Added ``OIDC_USE_HTTPS`` setting to allow non-https OIDC hosts
- Removed cluster validation from job-submission due to reliance on external cluster registry
- Added a `show-files` subcommand to `job-scripts` to show job script files
- Modified cache dir and dotenv path in order to avoid conflicts when installed alongside legacy jobbergate

## 3.2.4 -- 2022-09-12

- Refactor the logic to upload application files to the API.
- Remove file validation from the CLI.
- Remove compression of the upload files into tarballs.

## 3.2.3 -- 2022-08-01

- Patch cli authentication configurations.
- Added support to release on PyPI.

## 3.2.2 -- 2022-07-28

- Keep version in sync with the API.

## 3.2.1 -- 2022-06-24

- Keep version in sync with the API.

## 3.2.0 -- 2022-06-24

- Set ``environment`` variable for Sentry based on settings parameter.
- Adjusted variables and data structures for keycloak migration

## 3.1.1 -- 2022-06-01

- Added warning and handling for empty access tokens in the cache.

## 3.1.0 -- 2022-04-20

- Added execution_directory to job submissions
- Added checks for empty cached token files

## 3.0.4 -- 2022-04-11

- Made supplying param_dict optional in API job-scripts create.
- Included some example scripts for working with API directly.

## 3.0.3 -- 2022-04-08

- Restored jobberappslib (with deprecation warnings as appropriate)

## 3.0.2 -- 2022-04-08

- Fixed compatiblity issues with python 3.6

## 3.0.1 -- 2022-04-08

- Fixed publish github action

## 3.0.0 -- 2022-04-04

- Complete re-write of the Jobbergate CLI
- Used typer to implement the application
- Styled user output with Rich formatting
- Broke the code up into modules and functions for easier maintenance and reading
- Refactored the question asking system in applications
- Added over 100 unit tests

## 2.2.9 -- 2022-02-16

- Added AUTH0_LOGIN_DOMAIN setting
- Adjusted auth workflow to prefer AUTH0_LOGIN_DOMAIN over AUTH0_DOMAIN

## 2.2.8 -- 2022-02-15

- Fixed job submission data format for creation POST request

## 2.2.7 -- 2022-02-15

- Applied fix for requests and added more debug logging

## 2.2.6 -- 2022-02-14

- Added search and sort capability to the list endpoints to the API

## 2.2.5 -- 2022-02-14

- Removed job_script_data_as_string from create parameters for job_script create in API

## 2.2.4 -- 2022-02-14

- Fixed urls in the CLI again

## 2.2.3 -- 2022-02-14

- Improved error messages for users and captured error info

## 2.2.2 -- 2022-02-07

- Fixed applicaiton creation

## 2.2.1 -- 2022-02-03

- Fixed issue with SENTRY_DSN shadowing API initialization

## 2.2.0 -- 2022-02-03

- Removed trailing slashes from api endpoints

## 2.1.2 -- 2022-02-02

- Revised login workflow to use client-credentials auth workflow
- Fixed IDENTITY_CLAIMS_KEY to be overrideable by environment

## 2.0.0 -- 2021-12-08

- Migrated from legacy jobbegate-cli project
