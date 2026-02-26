"""
Demonstrate creation of Jobbergate resources using API calls.

To run this example::

- Create a virtual environment to work in:
  $ python -m venv env

- Activate the virtual environment
  $ source env/bin/activate

- Install our one dependency
  $ pip install httpx

- Run the demo
  $ python create-with-api.py


Note: Before running this demo, you will need:

- A BASE_API_URL config set as an environment variable or in a `.env` file
- An Auth token in the same directory named "access.token".
  You may use the ``login-with-api.py`` for this.


Note:  If you want to use a local dev environment, you will need to follow the
instructions in the README of the `jobbergate-composed` directory to set up a local
environment using `docker-compose`. You will also need the following config settings::

- BASE_API_URL=http://localhost:8000
"""

import json
import os
import pathlib
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
base_api_url = os.getenv("BASE_API_URL")

access_token_file = pathlib.Path("./access.token")
token = access_token_file.read_text().rstrip()
application_path = pathlib.Path("./simple-application")


def create_application(
    application_name="demo-job-script",
):
    """
    Create an application from the "simple-application" example.
    """
    response = httpx.post(
        f"{base_api_url}/jobbergate/applications",
        headers=dict(Authorization=f"Bearer {token}"),
        json=dict(application_name=application_name),
    )
    response.raise_for_status()  # Raise an exception if status is not in 200s
    result = response.json()
    application_id = result["id"]
    print(f"Created application {application_id}")

    config_path = application_path / "jobbergate.yaml"
    source_path = application_path / "jobbergate.py"
    template_path = application_path / "templates" / "dummy-script.py.j2"

    with config_path.open("rb") as config_file:
        with source_path.open("rb") as source_file:
            with template_path.open("rb") as template_file:
                response = httpx.post(
                    f"{base_api_url}/jobbergate/applications/{application_id}/upload",
                    headers=dict(Authorization=f"Bearer {token}"),
                    files=[
                        ("upload_files", (config_path.name, config_file, "text/plain")),
                        ("upload_files", (source_path.name, source_file, "text/plain")),
                        ("upload_files", (template_path.name, template_file, "text/plain")),
                    ],
                )

    response.raise_for_status()  # Raise an exception if status is not in 200s
    print(f"Uploaded application files for application {application_id}")

    return application_id


def create_job_script(
    application_id,
    job_script_name="demo-job-script",
):
    """
    Create a job-script from the "simple-application".

    Application config params and sbatch params are hard-coded but may be easily modified as desired.
    """
    response = httpx.post(
        f"{base_api_url}/jobbergate/job-scripts",
        headers=dict(Authorization=f"Bearer {token}"),
        json=dict(
            application_id=application_id,
            job_script_name=job_script_name,
            job_script_description="A demonstration of job-script creation through the API",
            sbatch_params=[
                "--job-name Demooooooo",
                "--time 30",
            ],
            param_dict=dict(
                application_config=dict(
                    foo="foofoofoo",
                    bar="barbarbar",
                    baz="bazbazbaz",
                ),
            ),
        ),
    )
    response.raise_for_status()  # Raise an exception if status is not in 200s
    result = response.json()
    job_script_id = result["id"]
    print(f"Created job-script {job_script_id}")
    return job_script_id


def create_job_submission(
    job_script_id,
    job_submission_name="demo-job-sub",
):
    """
    Create a job-submission from a provided job_script_id.

    The job submission will be remotely submitted by the cluster-agent.
    """
    response = httpx.post(
        f"{base_api_url}/jobbergate/job-submissions",
        headers=dict(Authorization=f"Bearer {token}"),
        json=dict(
            job_script_id=job_script_id,
            job_submission_name=job_submission_name,
            client_id="local-slurm",
            job_script_description="A demonstration of job-submission creation through the API",
            execution_directory="/slurm-work-dir",
        ),
    )
    response.raise_for_status()  # Raise an exception if status is not in 200s
    result = response.json()
    job_submission_id = result["id"]
    print(f"Created job-submission {job_submission_id}")
    return job_submission_id


def watch_job_submission(
    job_submission_id,
):
    """
    Pull a job_submission data, print it if it has changed, and stop when it's done.
    """
    last_data = None
    status = None
    print(f"Watching job-submission {job_submission_id} for changes")
    while status not in ("REJECTED", "COMPLETED", "FAILED"):
        response = httpx.get(
            f"{base_api_url}/jobbergate/job-submissions/{job_submission_id}",
            headers=dict(Authorization=f"Bearer {token}"),
        )
        response.raise_for_status()  # Raise an exception if status is not in 200s
        result = response.json()
        if last_data != result:
            last_data = result
            print("Something changed!")
            print("Job Submission:")
            print(json.dumps(result, indent=2))
        else:
            print(".", end="", flush=True)
        status = result["status"]
        time.sleep(1)


if __name__ == "__main__":
    application_id = create_application()
    job_script_id = create_job_script(application_id)
    job_submission_id = create_job_submission(job_script_id)
    watch_job_submission(job_submission_id)
