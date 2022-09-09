"""
Demonstrate creation of a job-script from an application and subsequent submission through API calls.

To run this example::

- Create a virtual environment to work in:
  $ python -m venv env

- Activate the virtual environment
  $ source env/bin/activate

- Install our one dependency
  $ pip install httpx

- Run the demo
  $ python create-submit-job.py


Note: Before running this demo, you will need::

- An Auth token in the same directory named "access.token". You may use the ``cli-login.py`` for this.
- An application created from the "simple-application" example directory. It may already exist.
"""

import pathlib

import httpx


def get_application_id(
    base_api_url="https://armada-k8s.staging.omnivector.solutions/jobbergate",
    access_token_file=pathlib.Path("./access.token"),
    application_identifier="simple-application",
):
    """
    Get an application id for the application with the identifier "simple-application".
    """
    token = access_token_file.read_text()
    response = httpx.get(
        f"{base_api_url}/applications",
        headers=dict(Authorization=f"Bearer {token}"),
        params=dict(search=application_identifier),
    )
    response.raise_for_status()  # Raise an exception if status is not in 200s
    for result in response.json()["results"]:
        if result["application_identifier"] == application_identifier:
            application_id = result["id"]
            print(f"Found application id {application_id}")
            return application_id
    raise RuntimeError(f"Couldn't find an application with identifier='{application_identifier}'")


def create_job_script(
    application_id,
    base_api_url="https://armada-k8s.staging.omnivector.solutions/jobbergate",
    access_token_file=pathlib.Path("./access.token"),
    job_script_name="demo-job-script",
):
    """
    Create a job-script from the "simple-application".

    Application config params and sbatch params are hard-coded but may be easily modified as desired.
    """
    token = access_token_file.read_text()
    response = httpx.post(
        f"{base_api_url}/job-scripts",
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
    base_api_url="https://armada-k8s.staging.omnivector.solutions/jobbergate",
    access_token_file=pathlib.Path("./access.token"),
    job_submission_name="demo-job-sub",
):
    """
    Create a job-submission from a provided job_script_id.

    The job submission will be remotely submitted by the cluster-agent.
    """
    token = access_token_file.read_text()
    response = httpx.post(
        f"{base_api_url}/job-submissions",
        headers=dict(Authorization=f"Bearer {token}"),
        json=dict(
            job_script_id=job_script_id,
            job_submission_name=job_submission_name,
            job_script_description="A demonstration of job-submission creation through the API",
        ),
    )
    response.raise_for_status()  # Raise an exception if status is not in 200s
    result = response.json()
    job_submission_id = result["id"]
    print(f"Created job-submission {job_submission_id}")
    return job_submission_id


if __name__ == '__main__':
    application_id = get_application_id()
    job_script_id = create_job_script(application_id)
    job_submission_id = create_job_submission(job_script_id)
