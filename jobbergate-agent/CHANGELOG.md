# Change Log

This file keeps track of all notable changes to jobbergate-agent

## Unreleased

- Implement logic to retrieve job metrics data from InfluxDB and send it to the API. ([PENG-2457](https://sharing.clickup.com/t/h/c/18022949/PENG-2457/BU7UOA63B936N27))

## 5.4.0 -- 2024-11-18

- Changed auto-update task to reuse current scheduler instead of creating a new one
- Fixed environment variables from the machine running the agent propagating to slurm jobs (notice `--export=ALL` is the default behavior for sbatch)
- Removed the `OIDC_AUDIENCE` setting

## 5.3.0 -- 2024-09-09

- Fixed issue when downloading job script files for job submission with large names
- Cache slurm submissions to avoid the resubmission of the same job if the job status update fails [PENG-2342]

## 5.2.0 -- 2024-07-01
- Change pydantic.BaseSettings config to use `extra=ignore`
- Migrated to Pydantic version 2 [PENG-2278]
  - Upgraded pydantic to 2.7
  - Added pydantic-settings 2.2.1
- Upgraded mypy to 1.10
- Updated linter and format checker to use ruff

## 5.1.0 -- 2024-04-19

- Added a new task to report at the expected interval that the agent is up and running [ASP-4602]
- Patched cwd issues on remote job submission to avoid permission denied errors on the folder

## 5.0.0 -- 2024-04-18

- Added logic to update slurm job status at job submission time [PENG-2193]
- Hot fix regarding the self update task where tasks weren't properly scheduled after the version update
- Added a task scheduler whose purpose is to self update the agent [PENG-2116]
- Dropped support for Python 3.8 and 3.9
- Replaced slurmrestd as the way the agent interacts with slurm by using sbatch to submit jobs and scontrol to get information about them [ASP-4585]

## 4.4.0 -- 2024-03-19

- Keep version in sync with the other components.

## 4.3.0 -- 2024-02-14

- Revamped job_submissions statuses and tracked more details slurm job_state [PENG-2064]
  - Renamed the finish.py module to update.py
  - Changed logic such that all active jobs have their job state updated on each pass
  - Moved all logic from the api.py module to update.py and submit.py
  - Updated schemas for revised job payloads
  - Updated and added unit tests
- Added the job property `environment` since it is required when configured to interact with slurm rest `0.0.39`
- Map job submissions with cancelled status [ASP-4288]

## 4.2.0 -- 2024-01-08

- Capture request errors with Slurm API in Sentry notifications [PENG-2000]
- Capture request errors with Jobbergate API in Sentry notifications [PENG-2000]
- Added support for Python 3.12
- Added setting to specify if the job script files should be written to the submit directory [ASP-4245]
- Added setting to control the timeout on `httpx` requests

## 4.1.0 -- 2023-11-07

- Keep version in sync with the other components.

## 4.0.0 -- 2023-09-14

- Started the project
