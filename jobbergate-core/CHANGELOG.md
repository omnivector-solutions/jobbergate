# Change Log

This file keeps track of all notable changes to jobbergate-core

## Unreleased


## 5.4.0a0 -- 2024-11-04
- Removed the `OIDC_AUDIENCE` setting

## 5.3.0 -- 2024-09-09

- Refined authentication handler to get it ready to be used on the CLI and enable auto-login [ASP-4779]
  - Created a request handler to facilitate the communication with OIDC
  - Added Pydantic back as a dependency and applied it to validate responses from the OIDC server
  - Created extra exceptions to handle authentication errors, that in turn can be more easily handled by client code

## 5.2.0 -- 2024-07-01
- Removed unused dependency for pydantic
- Updated linter and format checker to use ruff

## 5.1.0 -- 2024-04-19

- Refactored the command handler that interfaces with sbatch and scontrol

## 5.0.0 -- 2024-04-18

- Dropped support for Python 3.8 and 3.9
- Added helpers to interact with Slurm by using sbatch to submit jobs and scontrol que get information about them [ASP-4585]

## 4.4.0 -- 2024-03-19

- Keep version in sync with the other components.

## 4.3.0 -- 2024-02-14

- Keep version in sync with the other components.

## 4.2.0 -- 2024-01-08

- Added support for Python 3.12

## 4.1.0 -- 2023-11-07

- Keep version in sync with the other components.

## 4.0.0 -- 2023-09-14

- Keep version in sync with the other components.
