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


async def publish_status_change(
    job_submission: JobSubmission,
    organization_id: Optional[str] = None,
):
    """
    Publish a status change for a JobSubmission to the RabbitMQ exchange used for notifications.
    """
    if settings.RABBITMQ_HOST is None:
        return

    logger.debug("Publishing status change to notification queue")

    try:
        message_payload = dict(
            path=f"jobs.job_submissions.{job_submission.id}",
            user_email=job_submission.owner_email,
            action="status",
            additional_context=dict(
                status=job_submission.status,
                slurm_job_state=job_submission.slurm_job_state,
            ),
        )
        async with rabbitmq_connect(exchange_name=organization_id) as (exchange, _):
            await exchange.publish(
                message=aio_pika.Message(
                    body=json.dumps(message_payload).encode("utf-8"),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers=dict(organization=organization_id),
                ),
                routing_key="status",
            )
    except Exception as exc:
        logger.error("Failed to publish status change notification")
        logger.exception(exc)
