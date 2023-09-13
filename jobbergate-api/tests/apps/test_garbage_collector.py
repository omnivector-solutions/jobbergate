"""Tests for the garbage collector."""

from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks

from jobbergate_api.apps.garbage_collector import (
    delete_files_from_bucket,
    garbage_collect,
    get_files_to_delete,
    get_set_of_files_from_bucket,
    get_set_of_files_from_database,
)
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplateFile


@pytest.fixture
async def file_service(synth_services, fill_job_template_data):
    await synth_services.crud.template.create(**fill_job_template_data(id=13))
    yield synth_services.file.template


@pytest.fixture
def insert_file(file_service):
    """
    Combine user supplied application data with defaults. If there are overlaps, use the user supplied data.
    """

    async def _helper(**fields):
        file_data = {
            "parent_id": 13,
            "filename": "test.txt",
            "upload_content": "test file content",
            "file_type": "ENTRYPOINT",
            **fields,
        }
        template_file = await file_service.upsert(**file_data)
        return template_file

    return _helper


async def test_get_set_of_files_from_database(synth_session, insert_file):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    db_files = await get_set_of_files_from_database(synth_session, JobScriptTemplateFile)
    assert sorted(db_files) == sorted(
        [
            file1.file_key,
            file2.file_key,
            file3.file_key,
        ]
    )


async def test_get_set_of_files_from_bucket(synth_session, synth_bucket, insert_file):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    bucket_files = await get_set_of_files_from_bucket(synth_bucket, JobScriptTemplateFile)
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file2.file_key,
            file3.file_key,
        ]
    )


async def test_get_files_to_delete(synth_session, synth_bucket, insert_file):
    await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    await insert_file(filename="three.txt")

    file2_key = file2.file_key
    await synth_session.delete(file2)

    delete_files = await get_files_to_delete(synth_session, JobScriptTemplateFile, synth_bucket)
    assert delete_files == {file2_key}


async def test_delete_files_from_bucket(synth_session, synth_bucket, insert_file):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    file2_key = file2.file_key
    await synth_session.delete(file2)

    await delete_files_from_bucket(synth_bucket, {file2_key})

    bucket_files = await get_set_of_files_from_bucket(synth_bucket, JobScriptTemplateFile)
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file3.file_key,
        ]
    )


async def test_garbage_collect(synth_session, synth_bucket, insert_file):
    file1 = await insert_file(filename="one.txt")
    file2 = await insert_file(filename="two.txt")
    file3 = await insert_file(filename="three.txt")

    await synth_session.delete(file2)

    bg_tasks = BackgroundTasks()
    await garbage_collect(synth_session, synth_bucket, [JobScriptTemplateFile], bg_tasks)
    await bg_tasks()

    bucket_files = await get_set_of_files_from_bucket(synth_bucket, JobScriptTemplateFile)
    assert sorted(bucket_files) == sorted(
        [
            file1.file_key,
            file3.file_key,
        ]
    )
