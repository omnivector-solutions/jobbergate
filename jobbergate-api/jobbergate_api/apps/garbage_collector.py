"""Delete unused files from Jobbergate's file storage."""

import asyncio
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.protocols import FileModelProto
from jobbergate_api.safe_types import Bucket


@dataclass
class GarbageCollector:
    """
    Class to delete unused files from Jobbergate's file storage.
    """

    model_type: type[FileModelProto]
    bucket: Bucket
    session: AsyncSession

    def __post_init__(self) -> None:
        """Post-initialize method to set up extra internal details."""
        MAX_CONCURRENT_REQUESTS = 25
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def run(self) -> None:
        """Delete files from the bucket."""
        logger.debug(f"Running garbage collector for {self.model_type.__tablename__}")
        files_to_delete = await self._get_files_to_delete()
        tasks = [self._delete_file(file) for file in files_to_delete]
        await asyncio.gather(*tasks)

    async def _delete_file(self, file: str) -> None:
        async with self.semaphore:
            obj = await self.bucket.Object(file)
            await obj.delete()
        logger.debug(f"Deleted file {file} from bucket {self.bucket.name}")

    async def _get_set_of_files_from_database(self) -> set[str]:
        """Get a set of files from the database."""
        rows = await self.session.execute(select(self.model_type))  # type: ignore
        result = {obj.file_key for obj in rows.scalars().all()}
        logger.debug(f"Total of files found in the table {self.model_type.__tablename__}: {len(result)}")
        return result

    async def _get_set_of_files_from_bucket(self) -> set[str]:
        """Get a set of files from the bucket."""
        prefix = self.model_type.__tablename__
        result = {obj.key async for obj in self.bucket.objects.filter(Prefix=prefix)}
        logger.debug(
            f"Total of files found in the bucket {self.bucket.name} with prefix {prefix}: {len(result)}"
        )
        return result

    async def _get_files_to_delete(self) -> set[str]:
        """Get a set of files to delete."""
        files_in_database = await self._get_set_of_files_from_database()
        files_in_bucket = await self._get_set_of_files_from_bucket()
        result = files_in_bucket - files_in_database
        logger.debug(f"Total of files to be garbage collected: {len(result)}")
        return result
