"""
Test the rabbitmq_notification module.
"""

import json
from unittest.mock import patch

import pytest

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.config import settings
from jobbergate_api.rabbitmq_notification import publish_status_change, rabbitmq_connect


@pytest.mark.flaky(max_runs=3)
async def test_publish_status_change__success(synth_services, tester_email):
    """
    Verify that publish_status_change publishes a status change notification to rabbitmq.

    This is an unstable test that may break when run with other tests that use rabbitmq. Thus,
    it is marked flaky.
    """

    dummy_job_submission = await synth_services.crud.job_submission.create(
        id=13,
        name="test_name",
        owner_email=tester_email,
        is_archived=False,
        client_id="dummy-client-id",
        status=JobSubmissionStatus.DONE,
        slurm_job_state=SlurmJobState.COMPLETED,
    )

    await publish_status_change(dummy_job_submission, organization_id="dummy-org")

    async with rabbitmq_connect(exchange_name="dummy-org", do_purge=True) as (_, queue):
        message = await queue.get(timeout=1)
        await message.ack()

    assert message
    assert message.headers == {"organization": "dummy-org"}
    assert json.loads(message.body.decode()) == {
        "path": "jobs.job_submissions.13",
        "user_email": tester_email,
        "action": "status",
        "additional_context": {
            "status": JobSubmissionStatus.DONE,
            "slurm_job_state": SlurmJobState.COMPLETED,
        },
    }


@pytest.mark.flaky(max_runs=3)
async def test_publish_status_change__default_exchange(synth_services, tester_email):
    """
    Verify that publish_status_change uses the default exchange name if organization_id is None.

    This is an unstable test that may break when run with other tests that use rabbitmq. Thus,
    it is marked flaky.
    """

    dummy_job_submission = await synth_services.crud.job_submission.create(
        id=13,
        name="test_name",
        owner_email=tester_email,
        is_archived=False,
        client_id="dummy-client-id",
        status=JobSubmissionStatus.DONE,
        slurm_job_state=SlurmJobState.COMPLETED,
    )

    await publish_status_change(dummy_job_submission)

    async with rabbitmq_connect(
        exchange_name=settings.RABBITMQ_DEFAULT_EXCHANGE,
        do_purge=True,
    ) as (_, queue):
        message = await queue.get(timeout=1)
        await message.ack()

    assert message
    assert message.headers == {"organization": None}
    assert json.loads(message.body.decode()) == {
        "path": "jobs.job_submissions.13",
        "user_email": tester_email,
        "action": "status",
        "additional_context": {
            "status": JobSubmissionStatus.DONE,
            "slurm_job_state": SlurmJobState.COMPLETED,
        },
    }


async def test_publish_status_change__does_nothing_if_RABBITMQ_HOST_is_undefined(
    synth_services,
    tester_email,
    tweak_settings,
):
    """
    Verify that publish_status_change does nothing if the RABBITMQ_HOST setting is undefined.
    """
    dummy_job_submission = await synth_services.crud.job_submission.create(
        id=13,
        name="test_name",
        owner_email=tester_email,
        is_archived=False,
        client_id="dummy-client-id",
        status=JobSubmissionStatus.DONE,
        slurm_job_state=SlurmJobState.COMPLETED,
    )

    with patch("jobbergate_api.rabbitmq_notification.aio_pika.connect_robust") as mock_connect:
        with tweak_settings(RABBITMQ_HOST=None):
            await publish_status_change(dummy_job_submission, organization_id="dummy-org")
            mock_connect.assert_not_called()
