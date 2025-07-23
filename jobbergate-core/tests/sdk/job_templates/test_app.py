import json
from typing import Any
import pytest
import respx
from httpx import Response, codes
from polyfactory.factories.pydantic_factory import ModelFactory

from jobbergate_core.sdk.constants import APPLICATION_SCRIPT_FILE_NAME
from jobbergate_core.sdk.job_templates.app import JobTemplates, TemplateFiles, WorkflowFiles
from jobbergate_core.sdk.job_templates.schemas import (
    JobTemplateBaseDetailedView,
    JobTemplateDetailedView,
    JobTemplateListView,
    TemplateFileDetailedView,
    WorkflowFileDetailedView,
)
from jobbergate_core.sdk.schemas import PydanticDateTime
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"

ModelFactory.add_provider(PydanticDateTime, lambda: ModelFactory.__faker__.date_time())


class TemplateFileDetailedViewFactory(ModelFactory[TemplateFileDetailedView]):
    """Factory for generating test data based on TemplateFileDetailedView objects."""

    __model__ = TemplateFileDetailedView


class WorkflowFileDetailedViewFactory(ModelFactory[WorkflowFileDetailedView]):
    """Factory for generating test data based on WorkflowFileDetailedView objects."""

    __model__ = WorkflowFileDetailedView


class JobTemplateBaseDetailedViewFactory(ModelFactory[JobTemplateBaseDetailedView]):
    """Factory for generating test data based on JobTemplateBaseDetailedView objects."""

    __model__ = JobTemplateBaseDetailedView


class JobTemplateDetailedViewFactory(ModelFactory[JobTemplateDetailedView]):
    """Factory for generating test data based on JobTemplateDetailedView objects."""

    __model__ = JobTemplateDetailedView


class JobTemplateListViewFactory(ModelFactory[JobTemplateListView]):
    """Factory for generating test data based on JobTemplateListView objects."""

    __model__ = JobTemplateListView


class TestTemplateFiles:
    template_files = TemplateFiles(client=Client(base_url=BASE_URL))

    def test_upsert(self, tmp_path, faker) -> None:
        """Test the upsert method of TemplateFiles."""
        response_data = TemplateFileDetailedViewFactory.build()
        file_path = tmp_path / response_data.filename
        file_content = faker.binary()
        job_template_id = response_data.parent_id
        file_type = response_data.file_type
        file_path.write_bytes(file_content)

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(
                f"/jobbergate/job-script-templates/{job_template_id}/upload/template/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))

            result = self.template_files.upsert(job_template_id, file_type, file_path)

        assert route.call_count == 1
        assert result == response_data

    def test_upsert_validation_error(self, tmp_path, faker) -> None:
        """Test the upsert method of TemplateFiles with a validation error."""
        response_data = TemplateFileDetailedViewFactory.build()
        file_path = tmp_path / response_data.filename
        file_content = faker.binary()
        job_template_id = response_data.parent_id
        file_type = response_data.file_type
        file_path.write_bytes(file_content)

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(
                f"/jobbergate/job-script-templates/{job_template_id}/upload/template/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.OK, json={"invalid": "data"}))

            with pytest.raises(JobbergateResponseError, match="Failed to validate response to model"):
                self.template_files.upsert(job_template_id, file_type, file_path)

        assert route.call_count == 1

    def test_upsert_io_error(self, tmp_path, faker) -> None:
        """Test the upsert method of TemplateFiles with an IO error."""
        response_data = TemplateFileDetailedViewFactory.build()
        file_path = tmp_path / response_data.filename
        file_content = faker.binary()
        job_template_id = response_data.parent_id
        file_type = response_data.file_type
        file_path.write_bytes(file_content)

        with respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(
                f"/jobbergate/job-script-templates/{job_template_id}/upload/template/{file_type.value}",
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))

            with pytest.raises(OSError):
                self.template_files.upsert(job_template_id, file_type, file_path.parent / "does-not-exist")

        assert route.call_count == 0

    def test_delete(self, faker) -> None:
        """Test the delete method of TemplateFiles."""
        file_name = faker.file_name()
        job_template_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.delete(
                f"/jobbergate/job-script-templates/{job_template_id}/upload/template/{file_name}"
            ).mock(return_value=Response(codes.OK))

            self.template_files.delete(job_template_id, file_name)

        assert route.call_count == 1


class TestWorkflowFiles:
    workflow_files = WorkflowFiles(client=Client(base_url=BASE_URL))

    def test_upsert(self, tmp_path, faker) -> None:
        """Test the upsert method of WorkflowFiles."""
        file_path = tmp_path / APPLICATION_SCRIPT_FILE_NAME
        file_content = faker.binary()
        response_data = WorkflowFileDetailedViewFactory.build()
        runtime_config = response_data.runtime_config
        job_template_id = response_data.parent_id
        file_path.write_bytes(file_content)

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route_kwargs: dict[str, Any] = dict(
                files={"upload_file": (file_path.name, file_content, "text/plain")},
            )
            if runtime_config is not None:
                route_kwargs["data"] = {"runtime_config": json.dumps(runtime_config)}
            route = respx_mock.put(
                f"/jobbergate/job-script-templates/{job_template_id}/upload/workflow",
                **route_kwargs,
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))

            result = self.workflow_files.upsert(job_template_id, file_path, runtime_config=runtime_config)

        assert route.call_count == 1
        assert result == response_data

    def test_delete(self, faker) -> None:
        """Test the delete method of WorkflowFiles."""
        job_template_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.delete(f"/jobbergate/job-script-templates/{job_template_id}/upload/workflow").mock(
                return_value=Response(codes.OK)
            )

            self.workflow_files.delete(job_template_id)

        assert route.call_count == 1


class TestJobTemplates:
    job_templates = JobTemplates(client=Client(base_url=BASE_URL))

    def test_clone(self, faker) -> None:
        """Test the clone method of JobTemplates."""
        response_data = JobTemplateDetailedViewFactory.build()
        clone_kwargs = {
            "name": faker.word(),
            "template_vars": {"key": "value"},
            "identifier": faker.uuid4(),
            "description": faker.sentence(),
        }
        job_template_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.post(
                f"/jobbergate/job-script-templates/clone/{job_template_id}",
                data=clone_kwargs,
            ).mock(return_value=Response(codes.CREATED, content=response_data.model_dump_json()))

            result = self.job_templates.clone(job_template_id, **clone_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_get_one(self, faker) -> None:
        """Test the get_one method of JobTemplates."""
        response_data = JobTemplateDetailedViewFactory.build()
        job_template_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get(f"/jobbergate/job-script-templates/{job_template_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            result = self.job_templates.get_one(job_template_id)

        assert route.call_count == 1
        assert result == response_data

    def test_list(self, faker, wrap_items_on_paged_response) -> None:
        """Test the list method of JobTemplates."""
        size = 5
        response_data = wrap_items_on_paged_response(JobTemplateListViewFactory.batch(size))
        list_kwargs = {
            "include_null_identifier": True,
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": size,
            "page": faker.random_int(),
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get("/jobbergate/job-script-templates", params=list_kwargs).mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            result = self.job_templates.get_list(**list_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_update(self, faker) -> None:
        """Test the update method of JobTemplates."""
        response_data = JobTemplateBaseDetailedViewFactory.build()
        job_template_id = faker.random_int()
        update_kwargs = {
            "name": faker.word(),
            "identifier": faker.uuid4(),
            "description": faker.sentence(),
            "template_vars": {"key": "value"},
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(
                f"/jobbergate/job-script-templates/{job_template_id}",
                data=update_kwargs,
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))

            result = self.job_templates.update(job_template_id, **update_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_delete(self, faker) -> None:
        """Test the delete method of JobTemplates."""
        job_template_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.delete(f"/jobbergate/job-script-templates/{job_template_id}").mock(
                return_value=Response(codes.NO_CONTENT)
            )

            self.job_templates.delete(job_template_id)

        assert route.call_count == 1
