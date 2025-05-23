import json
from typing import Any

import pendulum
import pytest
import respx
from httpx import Response

from jobbergate_core.sdk.constants import APPLICATION_SCRIPT_FILE_NAME, FileType
from jobbergate_core.sdk.job_templates.app import (
    JobTemplates,
    TemplateFiles,
    WorkflowFiles,
)
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"


def client_factory() -> Client:
    """Factory to create a Client instance."""
    return Client(base_url=BASE_URL)


def template_file_detailed_data_factory() -> dict[str, Any]:
    """Factory to create a detailed template file data."""
    return {
        "parent_id": 1,
        "filename": "test.txt",
        "file_type": "ENTRYPOINT",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
    }


def workflow_file_detailed_data_factory() -> dict[str, Any]:
    """Factory to create a detailed workflow file data."""
    return {
        "parent_id": 1,
        "filename": APPLICATION_SCRIPT_FILE_NAME,
        "runtime_config": {"foo": "bar"},
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
    }


def job_template_list_view_data_factory() -> dict[str, Any]:
    """Factory to create a list view from job template data."""
    return {
        "id": 1,
        "name": "template",
        "owner_email": "testing",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
        "is_archived": False,
        "description": "a template",
        "identifier": "test-app",
    }


def job_template_base_view_data_factory() -> dict[str, Any]:
    """Factory to create a list view from job template data."""
    return job_template_list_view_data_factory() | {"template_vars": {"foo": "bar"}}


def job_template_detailed_view_data_factory() -> dict[str, Any]:
    """Factory to create a detailed view from job template data."""
    return job_template_base_view_data_factory() | {
        "template_files": [template_file_detailed_data_factory()],
        "workflow_files": [workflow_file_detailed_data_factory()],
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


@respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
class TestTemplateFiles:
    template_files = TemplateFiles(client=client_factory())

    def test_upsert(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of TemplateFiles."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        response_data = template_file_detailed_data_factory()
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/template/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json=response_data))

        file_path.write_bytes(file_content)
        result = self.template_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

        assert result.parent_id == response_data["parent_id"]
        assert result.filename == response_data["filename"]
        assert result.file_type == response_data["file_type"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])

    def test_upsert_request_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of TemplateFiles with a request error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/template/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(500))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError):
            self.template_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

    def test_upsert_validation_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of TemplateFiles with a validation error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/template/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json={"invalid": "data"}))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError, match="Failed to validate response to model"):
            self.template_files.upsert(1, FileType.ENTRYPOINT, file_path)

        assert route.call_count == 1

    def test_upsert_io_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of TemplateFiles with an IO error."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/template/ENTRYPOINT",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json=template_file_detailed_data_factory()))

        with pytest.raises(OSError):
            self.template_files.upsert(1, FileType.ENTRYPOINT, file_path / "does-not-exist")

        assert route.call_count == 0

    def test_delete(self, respx_mock) -> None:
        """Test the delete method of TemplateFiles."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1/upload/template/test.txt").mock(
            return_value=Response(200)
        )

        self.template_files.delete(1, "test.txt")

        assert route.call_count == 1

    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of TemplateFiles with a request error."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1/upload/template/test.txt").mock(
            return_value=Response(500)
        )

        with pytest.raises(JobbergateResponseError):
            self.template_files.delete(1, "test.txt")

        assert route.call_count == 1

    def test_download(self, respx_mock, tmp_path) -> None:
        """Test the download method of TemplateFiles."""
        file_path = tmp_path / "test.txt"
        file_content = b"content"
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/template/test.txt").mock(
            return_value=Response(200, content=file_content)
        )

        result = self.template_files.download(1, "test.txt", tmp_path)
        assert result == file_path

        assert route.call_count == 1
        assert result.exists()
        assert result.read_bytes() == file_content

    def test_download_request_error(self, respx_mock) -> None:
        """Test the download method of TemplateFiles with a request error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/template/test.txt").mock(
            return_value=Response(500)
        )

        with pytest.raises(JobbergateResponseError):
            self.template_files.download(1, "test.txt")

        assert route.call_count == 1

    def test_download_io_error(self, respx_mock, tmp_path) -> None:
        """Test the download method of TemplateFiles with an IO error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/template/test.txt").mock(
            return_value=Response(200, content=b"content")
        )

        with pytest.raises(JobbergateResponseError):
            self.template_files.download(1, filename="test.txt", directory=tmp_path / "does-not-exist")

        assert route.call_count == 1


class TestWorkflowFiles:
    workflow_files = WorkflowFiles(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of WorkflowFiles."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = b"content"
        response_data = workflow_file_detailed_data_factory()
        runtime_config = response_data["runtime_config"]
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/workflow",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
            data={"runtime_config": json.dumps(runtime_config)},
        ).mock(return_value=Response(200, json=response_data))

        file_path.write_bytes(file_content)
        result = self.workflow_files.upsert(1, file_path, runtime_config=runtime_config)

        assert route.call_count == 1

        assert result.parent_id == response_data["parent_id"]
        assert result.filename == response_data["filename"]
        assert result.runtime_config == response_data["runtime_config"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_no_file(self, respx_mock) -> None:
        """Test the upsert method of WorkflowFiles."""
        response_data = workflow_file_detailed_data_factory()
        runtime_config = response_data["runtime_config"]
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/workflow",
            data={"runtime_config": json.dumps(runtime_config)},
        ).mock(return_value=Response(200, json=response_data))

        result = self.workflow_files.upsert(1, runtime_config=runtime_config)

        assert route.call_count == 1

        assert result.parent_id == response_data["parent_id"]
        assert result.filename == response_data["filename"]
        assert result.runtime_config == response_data["runtime_config"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_no_config(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of WorkflowFiles."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = b"content"
        response_data = workflow_file_detailed_data_factory()
        del response_data["runtime_config"]
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/workflow",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json=response_data))

        file_path.write_bytes(file_content)
        result = self.workflow_files.upsert(1, file_path)

        assert route.call_count == 1

        assert result.parent_id == response_data["parent_id"]
        assert result.filename == response_data["filename"]
        assert result.runtime_config == {}
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_request_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of WorkflowFiles with a request error."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/workflow",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(500))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError):
            self.workflow_files.upsert(1, file_path)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_upsert_validation_error(self, respx_mock, tmp_path) -> None:
        """Test the upsert method of WorkflowFiles with a validation error."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = b"content"
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1/upload/workflow",
            files={"upload_file": (file_path.name, file_content, "text/plain")},
        ).mock(return_value=Response(200, json={"invalid": "data"}))

        file_path.write_bytes(file_content)
        with pytest.raises(JobbergateResponseError):
            self.workflow_files.upsert(1, file_path)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete(self, respx_mock) -> None:
        """Test the delete method of WorkflowFiles."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1/upload/workflow").mock(return_value=Response(200))

        self.workflow_files.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of WorkflowFiles with a request error."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1/upload/workflow").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.workflow_files.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download(self, respx_mock, tmp_path) -> None:
        """Test the download method of WorkflowFiles."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = b"content"
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/workflow").mock(
            return_value=Response(200, content=file_content)
        )

        result = self.workflow_files.download(1, tmp_path)

        assert result == file_path
        assert route.call_count == 1
        assert result.exists()
        assert result.read_bytes() == file_content

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download_request_error(self, respx_mock) -> None:
        """Test the download method of WorkflowFiles with a request error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/workflow").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.workflow_files.download(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_download_io_error(self, respx_mock, tmp_path) -> None:
        """Test the download method of WorkflowFiles with an IO error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1/upload/workflow").mock(
            return_value=Response(200, content=b"content")
        )

        with pytest.raises(JobbergateResponseError):
            self.workflow_files.download(1, directory=tmp_path / "does-not-exist")

        assert route.call_count == 1


class TestJobTemplates:
    job_templates = JobTemplates(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone(self, respx_mock) -> None:
        """Test the clone method of JobTemplates."""
        response_data = job_template_detailed_view_data_factory()
        clone_kwargs = {
            "name": "cloned",
            "template_vars": {"bar": "foo"},
            "identifier": "test-app",
            "description": "a template",
        }
        route = respx_mock.post("/jobbergate/job-script-templates/clone/1", data=clone_kwargs).mock(
            return_value=Response(201, json=response_data)
        )

        result = self.job_templates.clone(1, **clone_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]
        assert result.identifier == response_data["identifier"]
        assert result.template_vars == response_data["template_vars"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_request_error(self, respx_mock) -> None:
        """Test the clone method of JobTemplates with a request error."""
        route = respx_mock.post("/jobbergate/job-script-templates/clone/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.clone(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_validation_error(self, respx_mock) -> None:
        """Test the clone method of JobTemplates with a validation error."""
        route = respx_mock.post("/jobbergate/job-script-templates/clone/1").mock(
            return_value=Response(201, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_templates.clone(1, name="cloned")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create(self, respx_mock) -> None:
        """Test the create method of JobTemplates."""
        response_data = job_template_base_view_data_factory()
        create_kwargs = {
            "name": "created",
            "description": "a template",
            "identifier": "test-app",
            "template_vars": {"foo": "bar"},
        }
        route = respx_mock.post("/jobbergate/job-script-templates", data=create_kwargs).mock(
            return_value=Response(201, json=response_data)
        )

        result = self.job_templates.create(**create_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]
        assert result.identifier == response_data["identifier"]
        assert result.template_vars == response_data["template_vars"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_request_error(self, respx_mock) -> None:
        """Test the create method of JobTemplates with a request error."""
        route = respx_mock.post("/jobbergate/job-script-templates").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.create(name="created")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_validation_error(self, respx_mock) -> None:
        """Test the create method of JobTemplates with a validation error."""
        route = respx_mock.post("/jobbergate/job-script-templates").mock(
            return_value=Response(201, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_templates.create(name="created")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete(self, respx_mock) -> None:
        """Test the delete method of JobTemplates."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1").mock(return_value=Response(204))

        self.job_templates.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of JobTemplates with a request error."""
        route = respx_mock.delete("/jobbergate/job-script-templates/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one(self, respx_mock) -> None:
        """Test the get_one method of JobTemplates."""
        response_data = job_template_detailed_view_data_factory()
        route = respx_mock.get("/jobbergate/job-script-templates/1").mock(
            return_value=Response(200, json=response_data)
        )

        result = self.job_templates.get_one(1)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]
        assert result.identifier == response_data["identifier"]
        assert result.template_vars == response_data["template_vars"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_request_error(self, respx_mock) -> None:
        """Test the get_one method of JobTemplates with a request error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_validation_error(self, respx_mock) -> None:
        """Test the get_one method of JobTemplates with a validation error."""
        route = respx_mock.get("/jobbergate/job-script-templates/1").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_templates.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list(self, respx_mock) -> None:
        """Test the list method of JobTemplates."""
        response_data = pack_on_paginated_response(job_template_list_view_data_factory())
        list_kwargs = {
            "include_null_identifier": True,
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": 100,
            "page": 10,
        }
        route = respx_mock.get("/jobbergate/job-script-templates", params=list_kwargs).mock(
            return_value=Response(200, json=response_data),
        )

        result = self.job_templates.get_list(**list_kwargs)

        assert route.call_count == 1
        assert len(result.items) == 1
        assert result.items[0].id == response_data["items"][0]["id"]
        assert result.items[0].name == response_data["items"][0]["name"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_request_error(self, respx_mock) -> None:
        """Test the list method of JobTemplates with a request error."""
        route = respx_mock.get("/jobbergate/job-script-templates").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_validation_error(self, respx_mock) -> None:
        """Test the list method of JobTemplates with a validation error."""
        route = respx_mock.get("/jobbergate/job-script-templates").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_templates.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_update(self, respx_mock) -> None:
        """Test the update method of JobTemplates."""
        response_data = job_template_base_view_data_factory()
        update_kwargs: dict[str, Any] = {
            "name": "created",
            "identifier": "test-app",
            "description": "a template",
            "template_vars": {"foo": "bar"},
            # "is_archived": True,
        }
        route = respx_mock.put(
            "/jobbergate/job-script-templates/1",
            data=update_kwargs,
        ).mock(return_value=Response(200, json=response_data))

        result = self.job_templates.update(1, **update_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]
        assert result.identifier == response_data["identifier"]
        assert result.template_vars == response_data["template_vars"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_request_error(self, respx_mock) -> None:
        """Test the update method of JobTemplates with a request error."""
        route = respx_mock.put("/jobbergate/job-script-templates/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_templates.update(1, name="updated")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_validation_error(self, respx_mock) -> None:
        """Test the update method of JobTemplates with a validation error."""
        route = respx_mock.put("/jobbergate/job-script-templates/1").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_templates.update(1, name="updated")

        assert route.call_count == 1

    def test_template_files(self) -> None:
        """Test the files property of JobTemplates."""
        assert isinstance(self.job_templates.files.template, TemplateFiles)
        assert self.job_templates.files.template.client == self.job_templates.client
        assert self.job_templates.files.template.request_handler_cls == self.job_templates.request_handler_cls

    def test_workflow_files(self) -> None:
        """Test the files property of JobTemplates."""
        assert isinstance(self.job_templates.files.workflow, WorkflowFiles)
        assert self.job_templates.files.workflow.client == self.job_templates.client
        assert self.job_templates.files.workflow.request_handler_cls == self.job_templates.request_handler_cls
