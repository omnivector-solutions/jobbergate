# Change Log

This file keeps track of all notable changes to jobbergate-core

## Unreleased
- Revamped job_submissions statuses and tracked more details slurm job_state [PENG-2064]
  - Renamed the finish.py module to update.py
  - Changed logic such that all active jobs have their job state updated on each pass
  - Moved all logic from the api.py module to update.py and submit.py
  - Updated schemas for revised job payloads
  - Updated and added unit tests

## 4.3.0a6 -- 2024-02-06
## 4.3.0a5 -- 2024-02-02
## 4.3.0a4 -- 2024-01-31
## 4.3.0a3 -- 2024-01-31
## 4.3.0a2 -- 2024-01-29
## 4.3.0a1 -- 2024-01-24
- Added the job property `environment` since it is required when configured to interact with slurm rest `0.0.39`

## 4.3.0a0 -- 2024-01-15
## 4.2.1a0 -- 2024-01-11

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
