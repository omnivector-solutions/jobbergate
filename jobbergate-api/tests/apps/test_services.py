"""Test the database services."""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from itertools import product
from unittest import mock

import httpx
import pytest
from pydantic import AnyUrl
from fastapi import HTTPException, UploadFile
from fastapi_pagination.default import Params

from jobbergate_api.apps.models import Base, CrudMixin, FileMixin
from jobbergate_api.apps.services import CrudService, FileService, ServiceError


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
        tester_email,
    ):
        """
        Test that the ``create()`` method successfully creates an instance of the served model.
        """

        instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )

        assert instance.owner_email == tester_email
        assert isinstance(instance.id, int)

    async def test_clone_instance__success(self, dummy_crud_service, tester_email):
        """
        Test that the ``clone_instance`` method successfully clones an instance of the served model.
        """
        original_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )

        new_owner_email = "new_" + tester_email

        cloned_instance = await dummy_crud_service.clone_instance(
            original_instance,
            owner_email=new_owner_email,
        )

        assert cloned_instance.id != original_instance.id
        assert cloned_instance.owner_email == new_owner_email
        assert cloned_instance.name == original_instance.name
        assert cloned_instance.description == original_instance.description
        assert cloned_instance.cloned_from_id == original_instance.id

    async def test_clone_instance__type_error_on_unknown_column(self, dummy_crud_service, tester_email):
        """
        Test that the ``clone_instance`` raises a TypeError if an unknown column is passed to it.
        """
        instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )

        with pytest.raises(TypeError):
            await dummy_crud_service.clone_instance(instance, foo="bar")

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

    async def test_get__enforces_attributes(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``get()`` calls ``ensure_attribute()`` with the given attributes.

        Different scenarios are tested directly on the ``ensure_attribute()`` method.
        """
        test_name = "test-name"
        created_instance = await dummy_crud_service.create(
            name=test_name,
            owner_email=tester_email,
        )
        with mock.patch.object(dummy_crud_service, "ensure_attribute") as ensure_attribute:
            fetched_instance = await dummy_crud_service.get(
                created_instance.id, ensure_attributes=dict(owner_email=tester_email, name=test_name)
            )
        ensure_attribute.assert_called_once_with(created_instance, owner_email=tester_email, name=test_name)

        assert created_instance == fetched_instance

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
        await dummy_crud_service.create(name="one", owner_email="user1@test.com")
        await dummy_crud_service.create(name="two", owner_email="user2@test.com")
        await dummy_crud_service.create(name="three", owner_email="user1@test.com")

        all_fetched_instances = await dummy_crud_service.list(owner_email="user1@test.com")
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
        Test that the ``ensure_attribute()`` works when the entry is found and the emails match.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        dummy_crud_service.ensure_attribute(created_instance, owner_email=tester_email)

    async def test_get_ensure_attribute_multiple_arguments(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``ensure_attribute()`` method works with multiple arguments.
        """
        name = "test-name"
        created_instance = await dummy_crud_service.create(
            name=name,
            description="test-description",
            owner_email=tester_email,
        )
        dummy_crud_service.ensure_attribute(created_instance, owner_email=tester_email, name=name)

    async def test_get_ensure_ownership__bad_request(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``ensure_attribute()`` raises AttributeError when a column is not found.

        This is a sanity check, error handling may be improved in the future.
        """
        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=tester_email,
        )
        with pytest.raises(AttributeError):
            dummy_crud_service.ensure_attribute(created_instance, not_a_column="any-value")

    async def test_get_ensure_ownership__forbidden(
        self,
        dummy_crud_service,
        tester_email,
    ):
        """
        Test that the ``ensure_attribute()`` returns 403 when emails do not match.

        Also makes sure the context manager does not delete the entry.
        """
        owner_email = tester_email
        requester_email = "another_" + tester_email

        created_instance = await dummy_crud_service.create(
            name="test-name",
            description="test-description",
            owner_email=owner_email,
        )

        with pytest.raises(HTTPException) as exc_info:
            dummy_crud_service.ensure_attribute(created_instance, owner_email=requester_email)
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
            yield UploadFile(file_handle, filename=file_path.name, size=file_path.stat().st_size)

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

    async def test_clone_instance__success(self, dummy_file_service):
        """
        Test that the ``clone_instance`` method successfully clones an instance of the served model.
        """
        filename = "file-one.txt"
        file_content = b"dummy string content"

        original_instance = await dummy_file_service.upsert(13, filename, file_content)

        cloned_instance = await dummy_file_service.clone_instance(original_instance, 14)

        assert cloned_instance.parent_id != original_instance.parent_id
        assert cloned_instance.parent_id == 14
        assert cloned_instance.filename == filename
        assert cloned_instance.file_key != original_instance.file_key
        assert await dummy_file_service.get_file_content(cloned_instance) == file_content

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

    @pytest.mark.parametrize("file_content", ["dummy string content", ""])
    async def test_upsert__with_string(self, file_content, dummy_file_service):
        """
        Test that the ``upsert()`` method can create a file from a string.
        """
        upserted_instance = await dummy_file_service.upsert(13, "file-one.txt", file_content)

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == file_content.encode()

    @pytest.mark.parametrize("file_content", [b"dummy bytes content", b""])
    async def test_upsert__with_bytes(self, file_content, dummy_file_service):
        """
        Test that the ``upsert()`` method can create a file from bytes.
        """
        upserted_instance = await dummy_file_service.upsert(13, "file-one.txt", file_content)

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == file_content

    @pytest.mark.parametrize("file_content", [b"dummy bytes content", b""])
    async def test_upsert__with_url(self, file_content, dummy_file_service, respx_mock):
        """
        Test that the ``upsert()`` method can create a file from a file url.
        """
        respx_mock.get("http://dummy-domain.com/dummy-file.txt").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                content=file_content,
            ),
        )
        upserted_instance = await dummy_file_service.upsert(
            13,
            "file-one.txt",
            AnyUrl("http://dummy-domain.com/dummy-file.txt"),
        )

        assert upserted_instance.parent_id == 13
        assert upserted_instance.filename == "file-one.txt"

        file_data = await dummy_file_service.get_file_content(upserted_instance)
        assert file_data == file_content

    @pytest.mark.parametrize(
        "filename, content",
        [
            ("name.py", "dummy string content"),
            ("name.yaml", "unbalanced blackets: ]["),
            ("name.sh.jinja2", "Hello {{ name }!"),
            ("name.sh.j2", "Hello {{ name }!"),
        ],
    )
    async def test_upsert__raises_400_on_invalid_syntax(self, filename, content, dummy_file_service):
        """
        Test that the ``upsert()`` method raises a 400 error if the file syntax is invalid.
        """
        with pytest.raises(HTTPException) as exc_info:
            await dummy_file_service.upsert(13, filename, content)
        assert exc_info.value.status_code == 400
        assert "did not pass the syntax check" in exc_info.value.detail

    async def test_upsert__raises_500_no_size_attribute(self, make_upload_file, dummy_file_service):
        """
        Test that the ``upsert()`` method raises a 413 error if the file is too large.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy upload content") as dummy_upload_file:
            dummy_upload_file.size = None
            with pytest.raises(HTTPException, match="UploadFile has no size attribute") as exc_info:
                await dummy_file_service.upsert(13, "file-one.txt", dummy_upload_file)
        assert exc_info.value.status_code == 500

    async def test_upsert__raises_413_too_large(self, make_upload_file, dummy_file_service, tweak_settings):
        """
        Test that the ``upsert()`` method raises a 413 error if the file is too large.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy upload content") as dummy_upload_file:
            with tweak_settings(MAX_UPLOAD_FILE_SIZE=1):
                with pytest.raises(HTTPException, match="Uploaded files cannot exceed 1 bytes") as exc_info:
                    await dummy_file_service.upsert(13, "file-one.txt", dummy_upload_file)
        assert exc_info.value.status_code == 413

    @pytest.mark.parametrize(
        "file_content,protocol",
        product(
            [b"dummy bytes content", b""],
            ["http", "https"],
        ),
    )
    async def test__get_file_data_from_url__http_https(
        self, file_content, protocol, dummy_file_service, respx_mock
    ):
        """
        Test that the ``_get_file_data_from_url()`` method can download file data from http/https urls.
        """
        file_url = f"{protocol}://dummy-domain.com/dummy-file.txt"
        respx_mock.get(file_url).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                content=file_content,
            ),
        )
        file_obj = await dummy_file_service._get_file_data_from_url(AnyUrl(file_url))
        assert file_obj.read() == file_content

    @pytest.mark.parametrize(
        "file_content",
        [b"dummy bytes content", b""],
    )
    async def test__get_file_data_from_url__s3_success(self, file_content, dummy_file_service, respx_mock):
        """
        Test that the ``_get_file_data_from_url()`` method can download file data from s3 urls.

        Note that the s3 url is rewritten as an https url.
        """
        s3_url = "s3://dummy-bucket/dummy-file.txt"
        https_url = "https://dummy-bucket.s3.amazonaws.com/dummy-file.txt"
        respx_mock.get(https_url).mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                content=file_content,
            ),
        )
        file_obj = await dummy_file_service._get_file_data_from_url(AnyUrl(s3_url))
        assert file_obj.read() == file_content

    async def test__get_file_data_from_url__raises_500_if_download_fails(
        self, dummy_file_service, respx_mock
    ):
        """
        Test that the ``_get_file_data_from_url()`` method raises a 500 error if the download fails.
        """
        file_url = "https://dummy-domain.com/dummy-file.txt"

        respx_mock.get(file_url).mock(return_value=httpx.Response(httpx.codes.IM_A_TEAPOT))
        with pytest.raises(ServiceError, match="Failed to download") as exc_info:
            await dummy_file_service._get_file_data_from_url(AnyUrl(file_url))
        assert exc_info.value.status_code == 500

        respx_mock.get(file_url).mock(side_effect=RuntimeError)
        with pytest.raises(ServiceError, match="Failed to download") as exc_info:
            await dummy_file_service._get_file_data_from_url(AnyUrl(file_url))
        assert exc_info.value.status_code == 500

    @pytest.mark.parametrize(
        "file_url,error_stub",
        [
            [b"s3:", "Couldn't extract bucket name"],
            [b"s3://ultra-hpc.io", "Couldn't extract bucket key"],
        ],
    )
    async def test__get_file_data_from_url__s3_fails_on_invalid_url(
        self, file_url, error_stub, dummy_file_service
    ):
        """
        Test that the ``_get_file_data_from_url()`` method raises exeptions on invalid s3 urls.
        """
        with pytest.raises(ServiceError, match=error_stub):
            await dummy_file_service._get_file_data_from_url(AnyUrl(file_url))

    async def test__get_file_data_from_url__fails_on_unsupported_protocol(self, dummy_file_service):
        """
        Test that the ``_get_file_data_from_url()`` method raises exeptions on unsupported protocols.
        """
        with pytest.raises(ServiceError, match="Unsupported protocol"):
            await dummy_file_service._get_file_data_from_url(AnyUrl("ftp://ultra-hpc.io/target-file.txt"))

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

    async def test_render__raises_422_on_bad_template(self, make_upload_file, dummy_file_service):
        """
        Test that the ``render()`` method raises a 422 error if the template is invalid.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy {{ foo } content") as dummy_upload_file:
            upserted_instance = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )

        with pytest.raises(HTTPException) as exc_info:
            await dummy_file_service.render(upserted_instance, parameters=dict(foo="bar"))
        assert exc_info.value.status_code == 422
        assert "TemplateSyntaxError" in exc_info.value.detail
        assert "Unable to process jinja template filename=file-one.txt" in exc_info.value.detail

    async def test_render__backward_compatible(self, make_upload_file, dummy_file_service):
        """
        Test that the ``render()`` works in different contexts.
        """
        dummy_upload_file = make_upload_file()
        with make_upload_file(content="dummy {{ foo }} content") as dummy_upload_file:
            upserted_instance_1 = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )
            rendered_reference = await dummy_file_service.render(
                upserted_instance_1, parameters=dict(foo="bar")
            )

        with make_upload_file(content="dummy {{ data.foo }} content") as dummy_upload_file:
            upserted_instance_3 = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )
            rendered_legacy = await dummy_file_service.render(
                upserted_instance_3, parameters=dict(data=dict(foo="bar"))
            )

        assert rendered_reference == rendered_legacy

        with make_upload_file(content="dummy {{ data.foo }} content") as dummy_upload_file:
            upserted_instance_2 = await dummy_file_service.upsert(
                13,
                "file-one.txt",
                dummy_upload_file,
            )
            rendered_backward_compatible = await dummy_file_service.render(
                upserted_instance_2, parameters=dict(foo="bar")
            )

        assert rendered_reference == rendered_backward_compatible
