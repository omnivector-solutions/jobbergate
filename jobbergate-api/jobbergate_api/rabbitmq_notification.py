"""
RabbitMQ notification system for Jobbergate.
"""

import asyncio
import json
import socket
from contextlib import asynccontextmanager
from typing import Optional

import aio_pika
from loguru import logger

from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.config import settings
from jobbergate_api.retry_utils import async_retry


@asynccontextmanager
async def rabbitmq_connect(
    exchange_name=None,
    do_purge=False,
):
    """
    Connect to a RabbitMQ queue and exchange.
    """
    if exchange_name is None:
        exchange_name = settings.RABBITMQ_DEFAULT_EXCHANGE

    event_loop = asyncio.get_running_loop()
    connection = await aio_pika.connect_robust(
        host=settings.RABBITMQ_HOST,
        login=settings.RABBITMQ_USERNAME,
        password=settings.RABBITMQ_PASSWORD,
        client_properties={"connection_name": socket.gethostname()},
        loop=event_loop,
    )
    channel = await connection.channel(publisher_confirms=True)
    exchange = await channel.declare_exchange(
        name=exchange_name,
        type=aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    queue_name = "jobs"
    routing_key = "status"
    declared_queue = await channel.declare_queue(name=queue_name, durable=True)
    await declared_queue.bind(exchange, routing_key)

    try:
        yield (exchange, declared_queue)

    finally:
        if do_purge:
            await declared_queue.purge(timeout=1)
        await declared_queue.unbind(exchange, routing_key)
        await connection.close()


async def _publish_message(
    exchange: aio_pika.Exchange,
    message_payload: dict,
    organization_id: Optional[str],
) -> None:
    """Publish a single message to RabbitMQ exchange."""
    await exchange.publish(
        message=aio_pika.Message(
            body=json.dumps(message_payload).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"organization": organization_id},
        ),
        routing_key="status",
    )


async def publish_status_change(
    job_submission: JobSubmission,
    organization_id: Optional[str] = None,
) -> bool:
    """
    Publish a status change for a JobSubmission to the RabbitMQ exchange used for notifications.

    Returns True if successful, False if failed after max retries.
    """
    if settings.RABBITMQ_HOST is None:
        return True  # Skip when RabbitMQ is not configured

    logger.debug("Publishing status change to notification queue")

    message_payload = {
        "path": f"jobs.job_submissions.{job_submission.id}",
        "user_email": job_submission.owner_email,
        "action": "status",
        "additional_context": {
            "status": job_submission.status,
            "slurm_job_state": job_submission.slurm_job_state,
        },
    }

    async def _publish_with_connection():
        async with rabbitmq_connect(exchange_name=organization_id) as (exchange, _):
            await _publish_message(exchange, message_payload, organization_id)

    def on_retry_error(exc: Exception, attempt: int) -> None:
        logger.warning(f"Failed to publish status change notification (attempt {attempt}): {exc}")

    result = await async_retry(
        _publish_with_connection,
        max_attempts=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        on_error=on_retry_error,
    )

    if result is None:
        logger.error("Failed to publish status change notification after 3 retry attempts")
        return False

    return True
