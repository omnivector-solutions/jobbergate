"""Test the database services."""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from unittest import mock

import pytest
from fastapi import HTTPException, UploadFile
from fastapi_pagination.default import Params

from jobbergate_api.apps.models import Base, CrudMixin, FileMixin
from jobbergate_api.apps.services import CrudService, FileService


class DummyCrud(CrudMixin, Base):
    """
    A dummy model used for testing the CRUD service.
    """

    pass


@pytest.fixture
def dummy_crud_service(synth_session):
    """
    Provide a service that creates a CrudService for the DummyCrud and binds it to the synth_session.
    """
    service = CrudService(model_type=DummyCrud)
    with service.bound_session(synth_session):
        yield service


@pytest.fixture
def paginated():
    """
    Provide a context manager fixture that enables pagination.

    Note that without providing a FastAPI app and a route, pagination will throw an error due to having
    the ``resolve_params()`` method receiving no default params. This fixture patches the method to use
    the pagination parameters passed to the context manager.
    """

    @contextmanager
    def _helper(page=1, size=10):
        with mock.patch(
            "fastapi_pagination.api.resolve_params",
            side_effect=lambda _: Params(page=page, size=size),
        ):
            yield

    return _helper


def test_property__name(dummy_crud_service):
    """
    Test the name property.
    """
    assert dummy_crud_service.name == "dummy_cruds"


class TestCrudService:
    """
    Group tests for the CrudService.
    """

    async def test_create__success(
        self,
        dummy_crud_service,
        time_frame,
        tester_email,
    ):
        """
        Test that the ``create()`` method successfully creates an instance of the served model.
        """
        with time_frame() as window:
            instance = await dummy_crud_service.create(
                name="test-name",
                description="test-description",
                owner_email=tester_email,
            )

        assert instance.owner_email == tester_email
        assert instance.created_at in window
        assert instance.updated_at in window
        assert isinstance(instance.id, int)

    async def test_count__success(
        self,
        tester_email,
        dummy_crud_service,
    ):
        """
        Test that the ``count()`` method successfully counts all rows of the served model.
        """
        assert await dummy_crud_service.count() == 0
        for i in range(1, 4):
            await dummy_crud_service.create(
                name="test-name",
                description="test-description",
                owner_email=tester_email,
            )
            assert await dummy_crud_service.count() == i

    async def test_get__success(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get()`` method successfully retrieves an instance of the served model.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        fetched_instance = await dummy_crud_service.get(created_instance.id)
        assert created_instance == fetched_instance

    async def test_get__raises_exception_if_not_found(
        self,
        dummy_crud_service,
    ):
        """
        Test that the ``get()`` method raises an exception if no matching row of the served model are found.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.get(0)
        assert exc_info.value.status_code == 404

    async def test_delete__success_by_id(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``delete()`` method can remove a matching row of the served model from the database.
        """
        assert await dummy_crud_service.count() == 0
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        fetched_instance = await dummy_crud_service.get(created_instance.id)
        assert created_instance == fetched_instance

        await dummy_crud_service.delete(created_instance.id)
        assert await dummy_crud_service.count() == 0
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.get(created_instance.id)
        assert exc_info.value.status_code == 404

    async def test_delete__id_not_found(self, dummy_crud_service):
        """
        Test that the ``delete()`` method raises an exception if no matching row of the served model is found.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.delete(0)
        assert exc_info.value.status_code == 404

    async def test_update__success(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``update()`` method can update a matching row of the served model given a payload.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )

        fetched_instance = await dummy_crud_service.update(
            created_instance.id,
            name="new-name",
            description=None,
        )

        assert fetched_instance.id == created_instance.id
        assert fetched_instance.name == "new-name"

    async def test_update__not_found(self, dummy_crud_service):
        """
        Test that the ``update()`` method raises an exception if no matching row of the served model is found.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.update(
                0,
                name="new-name",
                description=None,
            )
        assert exc_info.value.status_code == 404

    async def test_list__unfiltered(
        self,
        dummy_crud_service,
    ):
        """
        Test that the unfiltered ``list()`` method returns all instances of the served model.
        """
        await dummy_crud_service.create(
            name="one",
            description="the first",
            owner_email="1@test.com",
        )
        await dummy_crud_service.create(
            name="two",
            description="second",
            owner_email="2@test.com",
        )
        await dummy_crud_service.create(
            name="three",
            description="a final instance",
            owner_email="3@test.com",
        )
        all_fetched_instances = await dummy_crud_service.list()
        assert ["one", "two", "three"] == [i.name for i in all_fetched_instances]

    async def test_list__include_archived(
        self,
        dummy_crud_service,
    ):
        """
        Test that the ``list()`` method returns all instances of the served model when including archived.

        Notice this is the default behavior.
        """
        await dummy_crud_service.create(
            name="one",
            description="the first",
            owner_email="1@test.com",
            is_archived=False,
        )
        await dummy_crud_service.create(
            name="two",
            description="second",
            owner_email="2@test.com",
            is_archived=True,
        )
        all_fetched_instances = await dummy_crud_service.list()
        assert ["one", "two"] == [i.name for i in all_fetched_instances]

    async def test_list__not_include_archived(
        self,
        dummy_crud_service,
    ):
        """
        Test that the ``list()`` method don not include archived instances.
        """
        await dummy_crud_service.create(
            name="one",
            description="the first",
            owner_email="1@test.com",
            is_archived=False,
        )
        await dummy_crud_service.create(
            name="two",
            description="second",
            owner_email="2@test.com",
            is_archived=True,
        )
        all_fetched_instances = await dummy_crud_service.list(include_archived=False)
        assert ["one"] == [i.name for i in all_fetched_instances]

    async def test_list__with_search(
        self,
        dummy_crud_service,
    ):
        """
        Test that the search filtered ``list()`` method finds all matching instances of the served model.
        """
        await dummy_crud_service.create(
            name="instance-one",
            description="the first",
            owner_email="user1@test.com",
        )
        await dummy_crud_service.create(
            name="item-two",
            description="second item",
            owner_email="user2@test.com",
        )
        await dummy_crud_service.create(
            name="instance-three",
            description="a final instance",
            owner_email="final@test.com",
        )

        all_fetched_instances = await dummy_crud_service.list(search="instance")
        assert ["instance-one", "instance-three"] == [i.name for i in all_fetched_instances]

        all_fetched_instances = await dummy_crud_service.list(search="user")
        assert ["user1@test.com", "user2@test.com"] == [i.owner_email for i in all_fetched_instances]

    async def test_list__with_sort(
        self,
        dummy_crud_service,
    ):
        """
        Test that the sorted ``list()`` method sorts all matching instances of the served model.
        """
        await dummy_crud_service.create(
            name="instance-one",
            description="the first",
            owner_email="user1@test.com",
        )
        await dummy_crud_service.create(
            name="item-two",
            description="second instance",
            owner_email="user2@test.com",
        )
        await dummy_crud_service.create(
            name="instance-three",
            description="a final instance",
            owner_email="final@test.com",
        )

        all_fetched_instances = await dummy_crud_service.list(sort_field="name")
        assert ["instance-one", "instance-three", "item-two"] == [i.name for i in all_fetched_instances]

        all_fetched_instances = await dummy_crud_service.list(sort_field="owner_email", sort_ascending=False)
        assert ["user2@test.com", "user1@test.com", "final@test.com"] == [
            i.owner_email for i in all_fetched_instances
        ]

    async def test_list__limited_by_owner(
        self,
        dummy_crud_service,
    ):
        """
        Test that the ``list()`` restricts instances of the served model to those owned by the user.
        """
        await dummy_crud_service.create(
            name="one",
            owner_email="user1@test.com",
        )
        await dummy_crud_service.create(
            name="two",
            owner_email="user2@test.com",
        )
        await dummy_crud_service.create(
            name="three",
            owner_email="user1@test.com",
        )

        all_fetched_instances = await dummy_crud_service.list(user_email="user1@test.com")
        assert ["one", "three"] == [i.name for i in all_fetched_instances]

    async def test_paginated_list(
        self,
        dummy_crud_service,
        paginated,
    ):
        """
        Test that the ``paginated_list()`` paginates matching instances of the served model.
        """
        await dummy_crud_service.create(
            name="one",
            description="the first",
            owner_email="1@test.com",
        )
        await dummy_crud_service.create(
            name="two",
            description="second",
            owner_email="2@test.com",
        )
        await dummy_crud_service.create(
            name="three",
            description="a final instance",
            owner_email="3@test.com",
        )

        with paginated(size=2):
            page = await dummy_crud_service.paginated_list()
        assert page.page == 1
        assert page.size == 2
        assert page.total == 3
        assert ["one", "two"] == [i.name for i in page.items]

        with paginated(page=2, size=2):
            page = await dummy_crud_service.paginated_list()
        assert page.page == 2
        assert page.size == 2
        assert page.total == 3
        assert ["three"] == [i.name for i in page.items]

        with paginated(page=2, size=1):
            page = await dummy_crud_service.paginated_list()
        assert page.page == 2
        assert page.size == 1
        assert page.total == 3
        assert ["two"] == [i.name for i in page.items]

    async def test_get_ensure_ownership__success(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get_ensure_ownership()`` method successfully retrieves an instance of the served model.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        fetched_instance = await dummy_crud_service.get_ensure_ownership(created_instance.id, tester_email)
        assert created_instance == fetched_instance

    async def test_get_ensure_ownership__bad_request(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get_ensure_ownership()`` returns 400 when the email provided is None.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.get_ensure_ownership(created_instance.id, None)
        assert exc_info.value.status_code == 400

    async def test_get_ensure_ownership__not_found(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get_ensure_ownership()`` returns 40f when the entry is not found.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.get_ensure_ownership(0, tester_email)
        assert exc_info.value.status_code == 404

    async def test_get_ensure_ownership__forbidden(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get_ensure_ownership()`` returns 403 when emails do not match.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        with pytest.raises(HTTPException) as exc_info:
            await dummy_crud_service.get_ensure_ownership(created_instance.id, "another_" + tester_email)
        assert exc_info.value.status_code == 403


class DummyFile(FileMixin, Base):
    """
    A dummy model used for testing the File service.
    """

    pass


@pytest.fixture
async def dummy_file_service(synth_session, synth_bucket):
    """
    Provide a service that creates a FileService for the DummyFile.

    Also bind the service to the synth_session and the test bucket.
    """
    service = FileService(model_type=DummyFile)
    with service.bound_session(synth_session):
        with service.bound_bucket(synth_bucket):
            yield service


@pytest.fixture
def make_upload_file(tmp_path):
    """
    Provide a context manager that creates a temporary file for testing uploads.
    """

    @contextmanager
    def _helper(filename="test.txt", content="test content"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        with open(file_path, "rb") as file_handle:
            yield UploadFile(file_handle, filename=file_path.name)

    return _helper


class TestFileService:
    """
    Group tests for the FileService.
    """

    async def test_get__success(
        self,
        dummy_file_service,
    ):
        """
        Test that the ``get()`` method successfully retrieves an instance of the served model.
        """
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy string content",
        )
        fetched_instance = await dummy_file_service.get(13, "file-one.txt")
        assert upserted_instance == fetched_instance

    async def test_get__raises_exception_if_not_found(
        self,
        dummy_file_service,
    ):
        """
        Test that the ``get()`` method raises an exception if no matching row of the served model are found.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_file_service.get(13, "file-one.txt")
        assert exc_info.value.status_code == 404

    async def test_find_children(self, dummy_file_service):
        """
        Test that the ``find_children()`` method correctly retrieves all entries with a parent.
        """
        matches = await dummy_file_service.find_children(13)
        assert matches == []

        await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy string content",
        )

        matches = await dummy_file_service.find_children(13)
        assert sorted([m.filename for m in matches]) == ["file-one.txt"]

        await dummy_file_service.upsert(
            13,
            "file-two.txt",
            "dummy string content",
        )
        matches = await dummy_file_service.find_children(13)
        assert sorted([m.filename for m in matches]) == ["file-one.txt", "file-two.txt"]

    async def test_stream_file_content__success(self, dummy_file_service):
        """
        Test that the ``get()`` method correctly retrieves a database entry.
        """
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy string content",
        )
        buff = BytesIO()
        async for chunk in await dummy_file_service.stream_file_content(upserted_instance):
            buff.write(chunk)

        buff.seek(0)
        assert buff.read() == "dummy string content".encode()

    async def test_stream_file_content__raises_500_if_file_is_missing(self, dummy_file_service, synth_bucket):
        """
        Test that the ``get()`` method raises a 500 error if the file is missing in s3.
        """
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy string content",
        )
        s3_object = await synth_bucket.Object(upserted_instance.file_key)
        await s3_object.delete()
        with pytest.raises(HTTPException) as exc_info:
            await dummy_file_service.stream_file_content(upserted_instance)
        assert exc_info.value.status_code == 500
        assert "file content not found" in exc_info.value.detail

    async def test_upsert__success(self, make_upload_file, dummy_file_service):
        """
        Test that the ``upsert()`` method correctly creates a database entry and file in the s3 store.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy upload content") as dummy_upload_file:
            upserted_instance = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == "dummy upload content".encode()

    async def test_upsert__with_string(self, dummy_file_service):
        """
        Test that the ``upsert()`` method can create a file from a string.
        """
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy string content",
        )

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == "dummy string content".encode()

    async def test_upsert__with_bytes(self, dummy_file_service):
        """
        Test that the ``upsert()`` method can create a file from bytes.
        """
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            "dummy bytes content".encode(),
        )

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == "dummy bytes content".encode()

    async def test_delete__success(self, make_upload_file, dummy_file_service):
        """
        Test that the ``delete()`` method removes the file from the storage and its row from the database.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy upload content") as dummy_upload_file:
            upserted_instance = await dummy_file_service.upsert(13, "file-one.txt", dummy_upload_file)

        await dummy_file_service.delete(upserted_instance)

        assert await dummy_file_service.find_children(13) == []
        with pytest.raises(HTTPException) as exc_info:
            await dummy_file_service.get_file_content(upserted_instance)
        assert exc_info.value.status_code == 500

    async def test_render__success(self, make_upload_file, dummy_file_service):
        """
        Test that the ``render()`` method can render a template loaded from the file store.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy {{ foo }} content") as dummy_upload_file:
            upserted_instance = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )

        assert (
            await dummy_file_service.render(upserted_instance, parameters=dict(foo="bar"))
            == "dummy bar content"
        )
