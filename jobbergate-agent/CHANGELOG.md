# Change Log

This file keeps track of all notable changes to jobbergate-agent

## Unreleased

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
