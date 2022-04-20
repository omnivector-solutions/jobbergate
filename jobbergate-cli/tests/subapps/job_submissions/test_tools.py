import json
import pathlib

import httpx

from jobbergate_cli.schemas import JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission, fetch_job_submission_data


def test_create_job_submission__success(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["job_submission_name"]
    job_submission_description = job_submission_data["job_submission_description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")

    new_job_submission = create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
    )
    assert new_job_submission == JobSubmissionResponse(**job_submission_data)


def test_create_job_submission__with_execution_dir(
    respx_mock,
    dummy_job_submission_data,
    dummy_domain,
    dummy_context,
    attach_persona,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_name = job_submission_data["job_submission_name"]
    job_submission_description = job_submission_data["job_submission_description"]

    job_script_id = job_submission_data["job_script_id"]

    create_job_submission_route = respx_mock.post(f"{dummy_domain}/job-submissions")
    create_job_submission_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_submission_data,
        ),
    )

    attach_persona("dummy@dummy.com")

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        execution_directory=pathlib.Path("/some/fake/path"),
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] == "/some/fake/path"

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        execution_directory=pathlib.Path("./some/relative/path"),
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] == str(pathlib.Path.cwd() / "./some/relative/path")

    create_job_submission(
        dummy_context,
        job_script_id,
        job_submission_name,
        job_submission_description,
        execution_directory=None,
    )
    payload = json.loads(create_job_submission_route.calls.last.request.content)
    assert payload["execution_directory"] is None


def test_fetch_job_submission_data__success__using_id(
    respx_mock,
    dummy_context,
    dummy_job_submission_data,
    dummy_domain,
):
    job_submission_data = dummy_job_submission_data[0]
    job_submission_id = job_submission_data["id"]
    fetch_route = respx_mock.get(f"{dummy_domain}/job-submissions/{job_submission_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=job_submission_data,
        ),
    )

    result = fetch_job_submission_data(dummy_context, job_submission_id)
    assert fetch_route.called
    assert result == JobSubmissionResponse(**job_submission_data)
