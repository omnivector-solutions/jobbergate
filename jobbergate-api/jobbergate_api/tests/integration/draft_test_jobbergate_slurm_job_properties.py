# type: ignore
"""
Integration tests for the job properties.

This is a draft of the tests that may be implemented in the future,
it was added to the version control as a reference for some of the
job properties that were already tested here.

In order to run these tests, you need to:
* Spin up jobbergate-composed (and have cloned of cluster-agent for that)
* Add hypothesis as a dependency for Jobbergate API
* Remove the prefix `draft` from the filename, so pytest can find it

Test based on cluster-agent >= 2.1.0.
"""

import json
from datetime import datetime, timedelta

import pydantic
import pytest
import requests
from hypothesis import example, given, settings
from hypothesis import strategies as st
from jose import jwt
from loguru import logger
from starlette import status

from jobbergate_api.apps.job_submissions.schemas import JobProperties


@pytest.fixture(scope="module")
def token():
    """
    Create a JWT token for the local-user.
    """
    now = datetime.now()
    payload = {
        "exp": int(datetime.timestamp(now + timedelta(seconds=900))),
        "iat": int(datetime.timestamp(now)),
        "sun": "local-user",
    }
    return jwt.encode(payload, "supersecret", algorithm="HS256")


class SlurmJobSubmission(pydantic.BaseModel):
    """
    Specialized model for describing a request to submit a job to Slurm REST API.
    """

    script: str
    job: JobProperties


def test_integration_ping(token):
    """
    Test that slurmrestd is up and running.
    """
    response = requests.get(
        url="http://localhost:6820/slurm/v0.0.36/ping",
        headers={
            "x-slurm-user-name": "local-user",
            "x-slurm-user-token": token,
        },
    )
    response.raise_for_status()


def submit_job_to_slurm(payload_json, token):
    """
    Test helper, used to submit a job to slurmrestd.
    """
    logger.debug(f"Payload: {payload_json}")

    response = requests.post(
        url="http://localhost:6820/slurm/v0.0.36/job/submit",
        headers={
            "x-slurm-user-name": "local-user",
            "x-slurm-user-token": token,
        },
        json=payload_json,
    )
    logger.debug(f"Slurmrestd response: {response.json()}")

    return response


@settings(deadline=None, report_multiple_bugs=True)
@given(
    instance=st.builds(
        JobProperties,
        get_user_environment=st.integers(min_value=0, max_value=1),
        hold=st.booleans(),
        kill_on_invalid_dependency=st.booleans(),
        memory_per_node=st.integers(min_value=1, max_value=100),
        requeue=st.booleans(),
        spread_job=st.booleans(),
        wait_all_nodes=st.integers(min_value=0, max_value=1),  # not bool as slurm's documentation suggests
    )
)
@example(instance=JobProperties(nodes="1-2"))
@example(instance=JobProperties(nodes="2"))
@example(instance=JobProperties(memory_per_node="1MB"))
@example(instance=JobProperties(time_limit="1:00:00"))
@example(instance=JobProperties(standard_output="/tmp"))
@example(instance=JobProperties(open_mode="append"))
@example(instance=JobProperties(open_mode="truncate"))
def test_integration_job_submit__success(instance, token):
    """
    Test that we can submit a job to slurmrestd.
    """
    dummy_job_script = "#!/bin/bash"

    payload = SlurmJobSubmission(script=dummy_job_script, job=instance)
    payload_json = json.loads(payload.json(exclude_none=True))

    response = submit_job_to_slurm(payload_json, token)
    response.raise_for_status()


@pytest.mark.parametrize(
    "job_properties",
    [
        {"nodes": [1, 2, 3]},
        {"nodes": [1]},
        # {"nodes": "1-2"}, this one works
        # {"nodes": 1}, this one works
        # {"nodes": "1"}, this one works
        {"no_kill": True},
        {"no_kill": False},
        {"no_kill": 1},
        {"no_kill": 0},
        # {"no_kill": None}, this one works
        {"time_minimum": 10},
        {"time_minimum": "1:00:00"},
        {"wait_all_nodes": True},
        {"wait_all_nodes": False},
    ],
)
def test_integration_job_submit__known_errors(job_properties, token):
    """
    Test that we get a 400 error when submitting a job with invalid properties.
    """
    job_properties["get_user_environment"] = 0

    payload_json = dict(script="#!/bin/bash", job=job_properties)

    response = submit_job_to_slurm(payload_json, token)
    with pytest.raises(requests.exceptions.HTTPError):
        response.raise_for_status()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
