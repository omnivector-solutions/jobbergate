import argparse
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from loguru import logger

from jobbergate_api.apps.dependencies import (
    Services,
    get_bucket_name,
    get_bucket_url,
    s3_bucket,
    service_factory,
)
from jobbergate_api.config import settings
from jobbergate_api.storage import engine_factory


@asynccontextmanager
async def cleanup_services(organization_id: str | None = None, commit=True) -> AsyncIterator[Services]:
    """Create a context manager for cleanup services."""
    override_base_name = organization_id if settings.MULTI_TENANCY_ENABLED else None
    bucket_name = get_bucket_name(override_base_name)
    s3_url = get_bucket_url()
    async with (
        s3_bucket(bucket_name, s3_url) as bucket,
        engine_factory.auto_session(override_base_name, commit=commit) as session,
    ):
        with service_factory(session, bucket) as services:
            yield services


async def run_cron_job(organization_id: str | None = None) -> None:
    """Run the cron jobs."""
    logger.info(f"Running cron jobs for organization ID: {organization_id}")
    async with cleanup_services(organization_id, commit=True) as services:
        for c in services.crud:
            await c.clean_unused_entries()

    async with cleanup_services(organization_id, commit=False) as services:
        for f in services.file:
            await f.clean_unused_files()

    logger.success(f"Finished running cron jobs for organization ID: {organization_id}")


async def main_async(targets: list[str] | list[None]) -> None:
    """Main function to run the cron jobs."""
    tasks = [run_cron_job(t) for t in targets]
    await asyncio.gather(*tasks)


def main() -> None:
    """Main function to run the cron jobs."""
    parser = argparse.ArgumentParser(description="Jobbergate API Cron Jobs")
    parser.add_argument(
        "--organization_id",
        "-i",
        type=str,
        action="append",
        default=[],
        help="Organization ID for multi-tenancy. Required when multi-tenancy is enabled.",
        required=settings.MULTI_TENANCY_ENABLED,
    )

    args = parser.parse_args()

    targets = args.organization_id if settings.MULTI_TENANCY_ENABLED else [None]
    asyncio.run(main_async(targets))
