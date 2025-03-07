from typing import Any

import pendulum
import pytest
import respx
from httpx import Response, codes
from polyfactory.factories.pydantic_factory import ModelFactory

from jobbergate_core.sdk.constants import FileType
from jobbergate_core.sdk.job_scripts.app import JobScriptFiles, JobScripts
from jobbergate_core.sdk.job_scripts.schemas import (
    JobScriptBaseView,
    JobScriptDetailedView,
    JobScriptFileDetailedView,
    JobScriptListView,
)
from jobbergate_core.sdk.schemas import PydanticDateTime
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"

ModelFactory.add_provider(PydanticDateTime, lambda: ModelFactory.__faker__.date_time())


class JobScriptFileDetailedViewFactory(ModelFactory[JobScriptFileDetailedView]):
    """Factory for generating test data based on JobScriptFileDetailedView objects."""

    __model__ = JobScriptFileDetailedView


class JobScriptBaseViewFactory(ModelFactory[JobScriptBaseView]):
    """Factory for generating test data based on JobScriptBaseView objects."""

    __model__ = JobScriptBaseView


class JobScriptListViewFactory(ModelFactory[JobScriptListView]):
    """Factory for generating test data based on JobScriptListView objects."""

    __model__ = JobScriptListView


class JobScriptDetailedViewFactory(ModelFactory[JobScriptDetailedView]):
    """Factory for generating test data based on JobScriptDetailedView objects."""

    __model__ = JobScriptDetailedView


def script_file_detailed_data_factory() -> dict[str, Any]:
    """Factory to create a detailed job script file data."""
    return {
        "parent_id": 1,
        "filename": "test.txt",
        "file_type": "ENTRYPOINT",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
    }


def job_script_list_view_data_factory() -> dict[str, Any]:
    """Factory to create a list view from job script data."""
    return {
        "id": 1,
        "name": "template",
        "owner_email": "testing",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
        "is_archived": False,
        "description": "a template",
    }


def job_script_base_view_data_factory() -> dict[str, Any]:
    """Factory to create a list view from job script data."""
    return job_script_list_view_data_factory()


def job_script_detailed_view_data_factory() -> dict[str, Any]:
    """Factory to create a detailed view from job template data."""
    return job_script_base_view_data_factory() | {
        "template_files": [script_file_detailed_data_factory()],
    }

class TestJobScriptFiles:
    job_script_files = JobScriptFiles(client=Client(base_url=BASE_URL))

    def test_upsert(self, respx_mock, tmp_path, faker) -> None:
        """Test the upsert method of ScriptFiles."""
        file_path = tmp_path / faker.file_name()
        file_content = faker.binary()
        response_data = JobScriptFileDetailedViewFactory.build()
        job_script_id = response_data.parent_id
        file_type = response_data.file_type
        file_path.write_bytes(file_content)

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.put(
                f"/jobbergate/job-scripts/{job_script_id}/upload/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))
            result = self.job_script_files.upsert(job_script_id, file_type, file_path)

        assert route.call_count == 1
        assert result == response_data

    def test_upsert_request_error(self, respx_mock, tmp_path, faker) -> None:
        """Test the upsert method of JobScriptFiles with a request error."""
        file_path = tmp_path / faker.file_name()
        file_content = faker.binary()
        job_script_id = faker.random_int()
        file_type = faker.random_element(FileType)
        file_path.write_bytes(file_content)

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.put(
                f"/jobbergate/job-scripts/{job_script_id}/upload/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.INTERNAL_SERVER_ERROR))
            self.job_script_files.upsert(job_script_id, file_type, file_path)

        assert route.call_count == 1

    def test_upsert_validation_error(self, respx_mock, tmp_path, faker) -> None:
        """Test the upsert method of JobScriptFiles with a validation error."""
        file_path = tmp_path / faker.file_name()
        file_content = faker.binary()
        job_script_id = faker.random_int()
        file_type = faker.random_element(FileType)
        file_path.write_bytes(file_content)

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError, match="Failed to validate response to model"),
        ):
            route = respx_mock.put(
                f"/jobbergate/job-scripts/{job_script_id}/upload/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.OK, json={"invalid": "data"}))
            self.job_script_files.upsert(job_script_id, file_type, file_path)

        assert route.call_count == 1

    def test_upsert_io_error(self, respx_mock, tmp_path, faker) -> None:
        """Test the upsert method of JobScriptFiles with an IO error."""
        file_path = tmp_path / faker.file_name()
        file_content = faker.binary()
        job_script_id = faker.random_int()
        file_type = faker.random_element(FileType)
        assert file_path.exists() is False

        with respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=True), pytest.raises(OSError):
            route = respx_mock.put(
                f"/jobbergate/job-scripts/{job_script_id}/upload/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            )
            self.job_script_files.upsert(job_script_id, file_type, file_path)

        assert route.call_count == 0

    def test_delete(self, respx_mock, faker) -> None:
        """Test the delete method of JobScriptFiles."""
        file_name = faker.file_name()
        job_script_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.delete(f"/jobbergate/job-scripts/{job_script_id}/upload/{file_name}").mock(
                return_value=Response(codes.OK)
            )
            self.job_script_files.delete(job_script_id, file_name)

        assert route.call_count == 1

    def test_delete_request_error(self, respx_mock, faker) -> None:
        """Test the delete method of JobScriptFiles with a request error."""
        file_name = faker.file_name()
        job_script_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.delete(f"/jobbergate/job-scripts/{job_script_id}/upload/{file_name}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_script_files.delete(job_script_id, file_name)

        assert route.call_count == 1

    def test_download(self, respx_mock, tmp_path, faker) -> None:
        """Test the download method of JobScriptFiles."""
        file_name = faker.file_name()
        file_content = faker.binary()
        job_script_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}/upload/{file_name}").mock(
                return_value=Response(codes.OK, content=file_content)
            )
            result = self.job_script_files.download(job_script_id, file_name, tmp_path)

        assert result == tmp_path / file_name
        assert route.call_count == 1
        assert result.exists()
        assert result.read_bytes() == file_content

    def test_download_request_error(self, respx_mock, tmp_path, faker) -> None:
        """Test the download method of JobScriptFiles with a request error."""
        file_name = faker.file_name()
        job_script_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}/upload/{file_name}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_script_files.download(job_script_id, file_name, tmp_path)

        assert route.call_count == 1
        assert (tmp_path / file_name).exists() is False

    def test_download_io_error(self, respx_mock, tmp_path, faker) -> None:
        """Test the download method of JobScriptFiles with an IO error."""
        file_name = faker.file_name()
        directory = tmp_path / faker.file_path(depth=2)
        job_script_id = faker.random_int()
        assert directory.exists() is False

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}/upload/{file_name}").mock(
                return_value=Response(codes.OK, content=b"content")
            )
            self.job_script_files.download(job_script_id, filename=file_name, directory=directory)

        assert route.call_count == 1
        assert (directory / file_name).exists() is False


class TestJobScripts:
    job_scripts = JobScripts(client=Client(base_url=BASE_URL))

    @pytest.mark.parametrize("include_description", [True, False])
    def test_clone(self, respx_mock, faker, include_description) -> None:
        """Test the clone method of JobScripts."""
        response_data = JobScriptDetailedViewFactory.build()
        clone_kwargs = {"name": response_data.name}
        if include_description:
            # Overwrite just in case Factory returns None to description
            clone_kwargs["description"] = faker.sentence()
        base_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.post(f"/jobbergate/job-scripts/clone/{base_id}", data=clone_kwargs).mock(
                return_value=Response(codes.CREATED, content=response_data.model_dump_json())
            )

            result = self.job_scripts.clone(base_id, **clone_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_clone_request_error(self, respx_mock, faker) -> None:
        """Test the clone method of JobScripts with a request error."""
        base_id = faker.random_int()
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.post(f"/jobbergate/job-scripts/clone/{base_id}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_scripts.clone(base_id)

        assert route.call_count == 1

    def test_clone_validation_error(self, respx_mock, faker) -> None:
        """Test the clone method of JobScripts with a validation error."""
        base_id = faker.random_int()
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.post(f"/jobbergate/job-scripts/clone/{base_id}").mock(
                return_value=Response(codes.CREATED, json={"invalid": "data"})
            )
            self.job_scripts.clone(base_id, name="cloned")

        assert route.call_count == 1

    @pytest.mark.parametrize("include_description", [True, False])
    def test_create(self, respx_mock, faker, include_description) -> None:
        """Test the create method of JobScripts."""
        response_data = JobScriptBaseViewFactory.build()
        create_kwargs = {"name": response_data.name}
        if include_description:
            # Overwrite just in case Factory returns None to description
            create_kwargs["description"] = faker.sentence()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.post("/jobbergate/job-scripts", data=create_kwargs).mock(
                return_value=Response(codes.CREATED, content=response_data.model_dump_json())
            )
            result = self.job_scripts.create(**create_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_create_request_error(self, respx_mock, faker) -> None:
        """Test the create method of JobScripts with a request error."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.post("/jobbergate/job-scripts").mock(return_value=Response(codes.BAD_REQUEST))
            self.job_scripts.create(name=faker.text())

        assert route.call_count == 1

    def test_create_validation_error(self, respx_mock, faker) -> None:
        """Test the create method of JobScripts with a validation error."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.post("/jobbergate/job-scripts").mock(
                return_value=Response(codes.CREATED, json={"invalid": "data"})
            )
            self.job_scripts.create(name=faker.text())

        assert route.call_count == 1

    def test_delete(self, respx_mock, faker) -> None:
        """Test the delete method of JobScripts."""
        job_script_id = faker.random_int()
        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.delete(f"/jobbergate/job-scripts/{job_script_id}").mock(
                return_value=Response(codes.NO_CONTENT)
            )
            result = self.job_scripts.delete(job_script_id)

        assert route.call_count == 1
        assert result is None

    def test_delete_request_error(self, respx_mock, faker) -> None:
        """Test the delete method of JobScripts with a request error."""
        job_script_id = faker.random_int()
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.delete(f"/jobbergate/job-scripts/{job_script_id}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_scripts.delete(job_script_id)

        assert route.call_count == 1

    def test_get_one(self) -> None:
        """Test the get_one method of JobScripts."""
        response_data = JobScriptDetailedViewFactory.build()
        job_script_id = response_data.id

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )
            result = self.job_scripts.get_one(job_script_id)

        assert route.call_count == 1
        assert result == response_data

    def test_get_one_request_error(self, faker) -> None:
        """Test the get_one method of JobScripts with a request error."""
        job_script_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_scripts.get_one(job_script_id)

        assert route.call_count == 1

    def test_get_one_validation_error(self, faker) -> None:
        """Test the get_one method of JobScripts with a validation error."""
        job_script_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/job-scripts/{job_script_id}").mock(
                return_value=Response(codes.OK, json={"invalid": "data"})
            )
            self.job_scripts.get_one(job_script_id)

        assert route.call_count == 1

    def test_list(self, faker, wrap_items_on_paged_response) -> None:
        """Test the list method of JobScripts."""
        size = 5
        response_data = wrap_items_on_paged_response(JobScriptListViewFactory.batch(size))
        list_kwargs = {
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": size,
            "page": faker.random_int(),
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get("/jobbergate/job-scripts", params=list_kwargs).mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json()),
            )
            result = self.job_scripts.get_list(**list_kwargs)

        assert route.call_count == 1
        assert result == response_data

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_request_error(self, respx_mock) -> None:
        """Test the list method of JobScripts with a request error."""
        route = respx_mock.get("/jobbergate/job-scripts").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_validation_error(self, respx_mock) -> None:
        """Test the list method of JobScripts with a validation error."""
        route = respx_mock.get("/jobbergate/job-scripts").mock(return_value=Response(200, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_update(self, respx_mock) -> None:
        """Test the update method of JobScripts."""
        response_data = job_script_base_view_data_factory()
        update_kwargs: dict[str, Any] = {
            "name": "created",
            "description": "a template",
            # "is_archived": True,
        }
        route = respx_mock.put(
            "/jobbergate/job-scripts/1",
            data=update_kwargs,
        ).mock(return_value=Response(200, json=response_data))

        result = self.job_scripts.update(1, **update_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_request_error(self, respx_mock) -> None:
        """Test the update method of JobScripts with a request error."""
        route = respx_mock.put("/jobbergate/job-scripts/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.update(1, name="updated")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_validation_error(self, respx_mock) -> None:
        """Test the update method of JobScripts with a validation error."""
        route = respx_mock.put("/jobbergate/job-scripts/1").mock(return_value=Response(200, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.update(1, name="updated")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_render_from_template(self, respx_mock) -> None:
        """Test the render_from_template method of JobScripts."""
        response_data = job_script_detailed_view_data_factory()
        create_kwargs: dict[str, Any] = {
            "name": "created",
            "description": "a template",
        }
        render_kwargs: dict[str, Any] = {
            "template_output_name_mapping": {"template.j2": "script.py"},
            "sbatch_params": ["--partition=debug", "--time=1:00:00"],
            "param_dict": {"param": "value"},
        }
        route = respx_mock.post(
            "/jobbergate/job-scripts/render-from-template/1",
            data={"create_request": create_kwargs, "render_request": render_kwargs},
        ).mock(return_value=Response(201, json=response_data))

        result = self.job_scripts.render_from_template(1, **create_kwargs, **render_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_render_from_template_request_error(self, respx_mock) -> None:
        """Test the render_from_template method of JobScripts."""
        create_kwargs: dict[str, Any] = {
            "name": "created",
            "description": "a template",
        }
        render_kwargs: dict[str, Any] = {
            "template_output_name_mapping": {"template.j2": "script.py"},
            "sbatch_params": ["--partition=debug", "--time=1:00:00"],
            "param_dict": {"param": "value"},
        }
        route = respx_mock.post(
            "/jobbergate/job-scripts/render-from-template/1",
            data={"create_request": create_kwargs, "render_request": render_kwargs},
        ).mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.render_from_template(1, **create_kwargs, **render_kwargs)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_render_from_template_validation_error(self, respx_mock) -> None:
        """Test the render_from_template method of JobScripts."""
        create_kwargs: dict[str, Any] = {
            "name": "created",
            "description": "a template",
        }
        render_kwargs: dict[str, Any] = {
            "template_output_name_mapping": {"template.j2": "script.py"},
            "sbatch_params": ["--partition=debug", "--time=1:00:00"],
            "param_dict": {"param": "value"},
        }
        route = respx_mock.post(
            "/jobbergate/job-scripts/render-from-template/1",
            data={"create_request": create_kwargs, "render_request": render_kwargs},
        ).mock(return_value=Response(201, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.render_from_template(1, **create_kwargs, **render_kwargs)

        assert route.call_count == 1

    def test_files(self) -> None:
        """Test the files property of JobScripts."""
        assert isinstance(self.job_scripts.files, JobScriptFiles)
        assert self.job_scripts.files.client == self.job_scripts.client
        assert self.job_scripts.files.request_handler_cls == self.job_scripts.request_handler_cls
