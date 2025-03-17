from typing import Any

import pendulum
import pytest
import respx
from httpx import Response

from jobbergate_core.sdk.constants import FileType
from jobbergate_core.sdk.job_scripts.app import JobScriptFiles, JobScripts
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"


def client_factory() -> Client:
    """Factory to create a Client instance."""
    return Client(base_url=BASE_URL)


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


def pack_on_paginated_response(data: dict[str, Any]) -> dict[str, Any]:
    """Pack data into a paginated response."""
    return {
        "items": [data],
        "total": 1,
        "page": 1,
        "size": 1,
        "pages": 1,
    }


class TestJobScriptFiles:
    job_script_files = JobScriptFiles(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of ScriptFiles."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        response_data = script_file_detailed_data_factory()
        route = respx_mock.put(
            "/jobbergate/job-scripts/1/upload/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json=response_data))

        file_path.write_bytes(file_content)
        result = self.job_script_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

        assert result.parent_id == response_data["parent_id"]
        assert result.filename == response_data["filename"]
        assert result.file_type == response_data["file_type"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_request_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of JobScriptFiles with a request error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-scripts/1/upload/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(500))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError):
            self.job_script_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_validation_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of JobScriptFiles with a validation error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-scripts/1/upload/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json={"invalid": "data"}))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError, match="Failed to validate response to model"):
            self.job_script_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=True)
    def test_upsert_io_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of JobScriptFiles with an IO error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-scripts/1/upload/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json=script_file_detailed_data_factory()))

        with pytest.raises(OSError):
            self.job_script_files.upsert(1, FileType.ENTRYPOINT, file_path / "does-not-exist")

        assert route.call_count == 0

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete(self, respx_mock) -> None:
        """Test the delete method of JobScriptFiles."""
        route = respx_mock.delete("/jobbergate/job-scripts/1/upload/test.txt").mock(return_value=Response(200))

        self.job_script_files.delete(1, "test.txt")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of JobScriptFiles with a request error."""
        route = respx_mock.delete("/jobbergate/job-scripts/1/upload/test.txt").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_script_files.delete(1, "test.txt")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download(self, respx_mock, tmp_path) -> None:
        """Test the download method of JobScriptFiles."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.get("/jobbergate/job-scripts/1/upload/test.txt").mock(
            return_value=Response(200, content=file_content)
        )

        result = self.job_script_files.download(1, "test.txt", tmp_path)
        assert result == file_path

        assert route.call_count == 1
        assert result.exists()
        assert result.read_bytes() == file_content

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download_request_error(self, respx_mock) -> None:
        """Test the download method of JobScriptFiles with a request error."""
        route = respx_mock.get("/jobbergate/job-scripts/1/upload/test.txt").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_script_files.download(1, "test.txt")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download_io_error(self, respx_mock, tmp_path) -> None:
        """Test the download method of JobScriptFiles with an IO error."""
        route = respx_mock.get("/jobbergate/job-scripts/1/upload/test.txt").mock(
            return_value=Response(200, content=b"content")
        )

        with pytest.raises(JobbergateResponseError):
            self.job_script_files.download(1, filename="test.txt", directory=tmp_path / "does-not-exist")

        assert route.call_count == 1


class TestJobScripts:
    job_scripts = JobScripts(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone(self, respx_mock) -> None:
        """Test the clone method of JobScripts."""
        response_data = job_script_detailed_view_data_factory()
        clone_kwargs = {
            "name": "cloned",
            "description": "a template",
        }
        route = respx_mock.post("/jobbergate/job-scripts/clone/1", data=clone_kwargs).mock(
            return_value=Response(201, json=response_data)
        )

        result = self.job_scripts.clone(1, **clone_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_request_error(self, respx_mock) -> None:
        """Test the clone method of JobScripts with a request error."""
        route = respx_mock.post("/jobbergate/job-scripts/clone/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.clone(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_validation_error(self, respx_mock) -> None:
        """Test the clone method of JobScripts with a validation error."""
        route = respx_mock.post("/jobbergate/job-scripts/clone/1").mock(
            return_value=Response(201, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.clone(1, name="cloned")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create(self, respx_mock) -> None:
        """Test the create method of JobScripts."""
        response_data = job_script_base_view_data_factory()
        create_kwargs = {
            "name": "created",
            "description": "a template",
        }
        route = respx_mock.post("/jobbergate/job-scripts", data=create_kwargs).mock(
            return_value=Response(201, json=response_data)
        )

        result = self.job_scripts.create(**create_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_request_error(self, respx_mock) -> None:
        """Test the create method of JobScripts with a request error."""
        route = respx_mock.post("/jobbergate/job-scripts").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.create(name="created")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_validation_error(self, respx_mock) -> None:
        """Test the create method of JobScripts with a validation error."""
        route = respx_mock.post("/jobbergate/job-scripts").mock(return_value=Response(201, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.create(name="created")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete(self, respx_mock) -> None:
        """Test the delete method of JobScripts."""
        route = respx_mock.delete("/jobbergate/job-scripts/1").mock(return_value=Response(204))

        self.job_scripts.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of JobScripts with a request error."""
        route = respx_mock.delete("/jobbergate/job-scripts/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one(self, respx_mock) -> None:
        """Test the get_one method of JobScripts."""
        response_data = job_script_detailed_view_data_factory()
        route = respx_mock.get("/jobbergate/job-scripts/1").mock(return_value=Response(200, json=response_data))

        result = self.job_scripts.get_one(1)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_request_error(self, respx_mock) -> None:
        """Test the get_one method of JobScripts with a request error."""
        route = respx_mock.get("/jobbergate/job-scripts/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_validation_error(self, respx_mock) -> None:
        """Test the get_one method of JobScripts with a validation error."""
        route = respx_mock.get("/jobbergate/job-scripts/1").mock(return_value=Response(200, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_scripts.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list(self, respx_mock) -> None:
        """Test the list method of JobScripts."""
        response_data = pack_on_paginated_response(job_script_list_view_data_factory())
        list_kwargs = {
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": 100,
            "page": 10,
        }
        route = respx_mock.get("/jobbergate/job-scripts", params=list_kwargs).mock(
            return_value=Response(200, json=response_data),
        )

        result = self.job_scripts.get_list(**list_kwargs)

        assert route.call_count == 1
        assert len(result.items) == 1
        assert result.items[0].id == response_data["items"][0]["id"]
        assert result.items[0].name == response_data["items"][0]["name"]

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
