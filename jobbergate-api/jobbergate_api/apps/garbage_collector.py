"""Delete unused files from jobbergate's file storage."""

import asyncio

from fastapi import BackgroundTasks
from loguru import logger
from sqlalchemy import select


async def get_set_of_files_from_database(session, table) -> set[str]:
    """Get a set of files from the database."""
    rows = await session.execute(select(table))
    result = {obj.file_key for obj in rows.scalars().all()}
    logger.debug(f"Total of files found in the table {table.__tablename__}: {len(result)}")
    return result


async def get_set_of_files_from_bucket(bucket, table) -> set[str]:
    """Get a set of files from the bucket."""
    prefix = table.__tablename__
    result = {obj.key async for obj in bucket.objects.filter(Prefix=prefix)}
    logger.debug(f"Total of files found in the bucket {bucket.name} with prefix {prefix}: {len(result)}")
    return result


async def get_files_to_delete(session, table, bucket) -> set[str]:
    """Get a set of files to delete."""
    files_in_database = await get_set_of_files_from_database(session, table)
    files_in_bucket = await get_set_of_files_from_bucket(bucket, table)
    result = files_in_bucket - files_in_database
    logger.debug(f"Total of files to be garbage collected: {len(result)}")
    return result


async def delete_files_from_bucket(bucket, files_to_delete: set[str]) -> None:
    """Delete files from the bucket."""
    MAX_CONCURRENT_REQUESTS = 25
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def delete_file(file: str) -> None:
        async with semaphore:
            obj = await bucket.Object(file)
            await obj.delete()
        logger.debug(f"Deleted file {file} from bucket {bucket.name}")

    tasks = [delete_file(file) for file in files_to_delete]
    await asyncio.gather(*tasks)


async def garbage_collector(session, bucket, list_of_tables, background_tasks: BackgroundTasks) -> None:
    """Delete unused files from jobbergate's file storage."""
    for table in list_of_tables:
        files_to_delete = await get_files_to_delete(session, table, bucket)
        if files_to_delete:
            background_tasks.add_task(delete_files_from_bucket, bucket, files_to_delete)
