"""Tests for the garbage collector."""

import asyncio
import pytest

from jobbergate_api.utils.garbage_collector import GarbageCollector


@pytest.fixture
async def file_service(synth_services):
    await synth_services.crud.template.create(
        id=1, name="test_name", owner_email="test_email", is_archived=False
    )
    yield synth_services.file.template


@pytest.fixture
def insert_file(file_service):
    """
    Combine user supplied application data with defaults. If there are overlaps, use the user supplied data.
    """

    async def _helper(**fields):
        file_data = {
            "parent_id": 1,
            "filename": "test.txt",
            "upload_content": "test file content",
            "file_type": "ENTRYPOINT",
            **fields,
        }
        template_file = await file_service.upsert(**file_data)
        return template_file

    return _helper


@pytest.fixture
def garbage_collector(file_service):
    """
    Create a garbage collector instance.
    """
    return GarbageCollector(
        table=file_service.model_type,
        bucket=file_service.bucket,
        session=file_service.session,
        semaphore=asyncio.Semaphore(),
    )


async def test_get_set_of_files_from_database(insert_file, garbage_collector):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    db_files = await garbage_collector._get_set_of_files_from_database()
    assert sorted(db_files) == sorted(
        [
            file1.file_key,
            file2.file_key,
            file3.file_key,
        ]
    )


async def test_get_set_of_files_from_bucket(insert_file, garbage_collector):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    bucket_files = await garbage_collector._get_set_of_files_from_bucket()
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file2.file_key,
            file3.file_key,
        ]
    )


async def test_get_files_to_delete(synth_session, insert_file, garbage_collector):
    await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    await insert_file(filename="three.txt")

    file2_key = file2.file_key
    await synth_session.delete(file2)

    delete_files = await garbage_collector._get_files_to_delete()
    assert delete_files == {file2_key}


async def test_delete_files_from_bucket(synth_session, insert_file, garbage_collector):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    file2_key = file2.file_key
    await synth_session.delete(file2)

    await garbage_collector._delete_file(file2_key)

    bucket_files = await garbage_collector._get_set_of_files_from_bucket()
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file3.file_key,
        ]
    )


async def test_garbage_collect(synth_session, insert_file, garbage_collector):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    await synth_session.delete(file2)

    await garbage_collector.run()

    bucket_files = await garbage_collector._get_set_of_files_from_bucket()
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file3.file_key,
        ]
    )
