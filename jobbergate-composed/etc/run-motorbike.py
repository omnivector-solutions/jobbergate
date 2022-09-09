#!/usr/bin/env python3

"""
Automatically runs through the process of clearing out the database and then running
the motorbike example with Jobbergate CLI.
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from loguru import logger


def main(verbose=True, clean=True):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)

    logger.info("Running motorbike example!")

    name = f"motorbike--{str(date.today())}"
    logger.debug(f"Using '{name}' for entity names in this run")

    try:
        subprocess.run("jobbergate show-token", check=True, shell=True, capture_output=True)
    except Exception as err:
        logger.debug("Logging in")
        subprocess.run("jobbergate login", check=True, shell=True)

    if clean:
        logger.info("Cleaning up any existing Jobbergate entities")
        tables_to_clear = ["job-submissions", "job-scripts", "applications"]
        for table in tables_to_clear:
            logger.debug(f"Deleting all existing {table}")
            proc = subprocess.run(
                f"jobbergate --raw {table} list",
                capture_output=True,
                shell=True,
            )
            if proc.stdout:
                for entry in json.loads(proc.stdout):
                    _id = entry["id"]
                    logger.debug(f"Deleting id {_id} from {table}...")
                    subprocess.run(f"jobbergate {table} delete --id={_id}", check=True, shell=True)
            else:
                logger.debug(f"No entries found in {table}. Skipping...")

    logger.info("Creating motorbike application")
    command = " ".join([
        "jobbergate",
        "--raw",
        "applications",
        "create",
        f"--name={name}",
        f"--identifier={name}",
        "--application-path=/motorbike-example",
    ])
    logger.debug(f"...with command `{command}`")
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=True,
    )
    logger.debug(f"...got output '{proc.stdout}'")
    data = json.loads(proc.stdout)
    application_id = data["id"]
    logger.info(f"Application created with {application_id=}")

    param_path = Path("/app/params.json")
    logger.debug(f"Creating param file for automatic parameters at {param_path}")
    param_path.write_text(json.dumps(dict(partition="compute", nodes=2, ntasks=4)))

    logger.info("Creating motorbike job script")
    command = " ".join([
        "jobbergate",
        "--raw",
        "job-scripts",
        "create",
        f"--name={name}",
        f"--application-id={application_id}",
        f"--param-file={param_path}",
        "--no-submit",
        "--no-fast",
    ])
    logger.debug(f"...with command `{command}`")
    proc = subprocess.run(
        command,
        capture_output=True,
        shell=True,
        text=True,
    )
    logger.debug(f"...got output '{proc.stdout}'")
    data = json.loads(proc.stdout)
    job_script_id = data["id"]
    logger.info(f"Job script created with {job_script_id=}")

    logger.info("Creating motorbike job submission")
    command = " ".join([
        "jobbergate",
        "--raw",
        "job-submissions",
        "create",
        f"--name={name}",
        f"--job-script-id={job_script_id}",
        f"--cluster-name=local-slurm",
    ])
    logger.debug(f"...with command `{command}`")
    proc = subprocess.run(
        command,
        capture_output=True,
        shell=True,
        text=True,
    )
    logger.debug(f"...got output '{proc.stdout}'")
    data = json.loads(proc.stdout)
    job_submission_id = data["id"]
    logger.info(f"Job submission created with {job_submission_id=}")

    command = " ".join([
        "jobbergate",
        "--raw",
        "job-submissions",
        "get-one",
        f"--id={job_submission_id}",
    ])
    logger.debug("Watching for job to be submitted...")
    status = None
    slurm_job_id = None
    while status != "SUBMITTED":
        proc = subprocess.run(
            command,
            capture_output=True,
            shell=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        status = data["status"]
        if status == "CREATED":
            continue
        elif status == "REJECTED":
            logger.warning("The job was rejected by Slurm!")
            sys.exit(1)
        elif status == "SUBMITTED":
            slurm_job_id = int(data["slurm_job_id"])
            logger.info(f"The job was successfully submitted to slurm with job id {slurm_job_id}!")
            pass
        else:
            logger.error("Job submission updated with unexpected status!")
            sys.exit(1)


    prefix = f"/nfs/R-motorbike.{slurm_job_id}"
    output_handler = None
    output_file_path = Path(f"{prefix}.out")
    slurm_job_id = None
    logger.debug("...waiting for output from submitted job (this may take a while)")
    while status not in ("COMPLETED", "FAILED"):
        if output_handler is None:
            if output_file_path.exists():
                output_handler = output_file_path.open()
        else:
            line = output_handler.readline()
            while line:
                logger.debug(f">>> {line.rstrip()}")
                line = output_handler.readline()

        proc = subprocess.run(
            command,
            capture_output=True,
            shell=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        status = data["status"]

    if status == "COMPLETED":
        logger.info("The job was completed successfully!")
    elif status == "FAILED":
        logger.error("The job failed:")
        error_file_path = Path(f"{prefix}.err")
        if error_file_path.exists():
            logger.error(f"Job Output:\n{error_file_path.read_text()}")


if __name__ == '__main__':
    typer.run(main)
