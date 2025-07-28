import json
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Type

from httpx import codes
from pydantic import ConfigDict, NonNegativeInt, PositiveInt, validate_call
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.constants import APPLICATION_SCRIPT_FILE_NAME, FileType
from jobbergate_core.sdk.job_templates.schemas import (
    JobTemplateBaseDetailedView,
    JobTemplateDetailedView,
    JobTemplateListView,
    TemplateFileDetailedView,
    WorkflowFileDetailedView,
)
from jobbergate_core.sdk.schemas import ListResponseEnvelope
from jobbergate_core.sdk.utils import filter_null_out, open_optional_file
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class TemplateFiles:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @validate_call
    def upsert(
        self, id_or_identifier: NonNegativeInt | str, file_type: FileType, file_path: Path
    ) -> TemplateFileDetailedView:
        """
        Upload or update a template file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            file_type: The type of the file.
            file_path: The path to the file to be uploaded.

        Returns:
            The detailed view of the template file.
        """
        with file_path.open("rb") as file:
            response = self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{file_type.value}",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (file_path.name, file, "text/plain")},
                ),
            )
        return response.raise_for_status().check_status_code(codes.OK).to_model(TemplateFileDetailedView)

    @validate_call
    def delete(self, id_or_identifier: NonNegativeInt | str, filename: str) -> None:
        """
        Delete a template file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            filename: The name of the file to be deleted.
        """
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{filename}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
        )

    @validate_call
    def download(self, id_or_identifier: NonNegativeInt | str, filename: str, directory: Path = Path.cwd()) -> Path:
        """
        Download a template file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            filename: The name of the file to be downloaded.
            directory: The directory where the file will be saved.

        Returns:
            The path to the downloaded file.
        """
        output_path = (directory / filename).resolve()
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{filename}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class WorkflowFiles:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @validate_call
    def upsert(
        self,
        id_or_identifier: NonNegativeInt | str,
        file_path: Path | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> WorkflowFileDetailedView:
        """
        Upload or update a workflow file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            file_path: The path to the file to be uploaded.
            runtime_config: The runtime configuration.

        Returns:
            The detailed view of the workflow file.
        """
        request_kwargs: dict[str, Any] = dict()
        if runtime_config is not None:
            request_kwargs["data"] = {"runtime_config": json.dumps(runtime_config)}
        with open_optional_file(file_path) as file:
            if file is not None:
                request_kwargs["files"] = {"upload_file": (APPLICATION_SCRIPT_FILE_NAME, file, "text/plain")}
            response = self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="PUT",
                request_kwargs=request_kwargs,
            )
        return response.raise_for_status().check_status_code(codes.OK).to_model(WorkflowFileDetailedView)

    @validate_call
    def delete(self, id_or_identifier: NonNegativeInt | str) -> None:
        """
        Delete a workflow file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
        """
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
        )

    @validate_call
    def download(self, id_or_identifier: NonNegativeInt | str, directory: Path = Path.cwd()) -> Path:
        """
        Download a workflow file.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            directory: The directory where the file will be saved.

        Returns:
            The path to the downloaded file.
        """
        output_path = directory / APPLICATION_SCRIPT_FILE_NAME
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Files:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @cached_property
    def template(self) -> TemplateFiles:
        """
        Get the TemplateFiles instance.

        Returns:
            The TemplateFiles instance.
        """
        return TemplateFiles(client=self.client, request_handler_cls=self.request_handler_cls)

    @cached_property
    def workflow(self) -> WorkflowFiles:
        """
        Get the WorkflowFiles instance.

        Returns:
            The WorkflowFiles instance.
        """
        return WorkflowFiles(client=self.client, request_handler_cls=self.request_handler_cls)


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class JobTemplates:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    base_path: ClassVar[str] = "/jobbergate/job-script-templates"

    @validate_call
    def clone(
        self,
        base_id_or_identifier: NonNegativeInt | str,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> JobTemplateDetailedView:
        """
        Clone a job template.

        Args:
            base_id_or_identifier: The ID or identifier of the base job template.
            name: The name of the new job template.
            identifier: The identifier of the new job template.
            description: The description of the new job template.
            template_vars: The template variables.

        Returns:
            The detailed view of the cloned job template.
        """
        data = filter_null_out(
            dict(name=name, identifier=identifier, description=description, template_vars=template_vars)
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/clone/{base_id_or_identifier}",
                method="POST",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def create(
        self,
        name: str,
        *,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> JobTemplateBaseDetailedView:
        """
        Create a new job template.

        Args:
            name: The name of the job template.
            identifier: The identifier of the job template.
            description: The description of the job template.
            template_vars: The template variables.

        Returns:
            The detailed view of the created job template.
        """
        data = filter_null_out(
            dict(name=name, identifier=identifier, description=description, template_vars=template_vars)
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="POST",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobTemplateBaseDetailedView)
        )

    @validate_call
    def delete(self, id_or_identifier: NonNegativeInt | str) -> None:
        """
        Delete a job template.

        Args:
            id_or_identifier: The ID or identifier of the job template.
        """
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(codes.NO_CONTENT)
        )

    @validate_call
    def get_one(self, id_or_identifier: NonNegativeInt | str) -> JobTemplateDetailedView:
        """
        Get a single job template.

        Args:
            id_or_identifier: The ID or identifier of the job template.

        Returns:
            The detailed view of the job template.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def get_list(
        self,
        include_null_identifier: bool = False,
        sort_ascending: bool = True,
        user_only: bool = False,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = False,
        size: PositiveInt = 50,
        page: PositiveInt = 1,
    ) -> ListResponseEnvelope[JobTemplateListView]:
        """
        List job templates.

        Args:
            include_null_identifier: Whether to include templates with null identifiers.
            sort_ascending: Whether to sort in ascending order.
            user_only: Whether to include only user-specific templates.
            search: The search query.
            sort_field: The field to sort by.
            include_archived: Whether to include archived templates.
            size: The number of templates per page.
            page: The page number.

        Returns:
            The list response envelope containing job template list views.
        """
        params = filter_null_out(
            dict(
                include_null_identifier=include_null_identifier,
                sort_ascending=sort_ascending,
                user_only=user_only,
                search=search,
                sort_field=sort_field,
                include_archived=include_archived,
                size=size,
                page=page,
            )
        )
        result = (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="GET",
                request_kwargs=dict(params=params),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(ListResponseEnvelope[JobTemplateListView])
        )
        return result

    @validate_call
    def update(
        self,
        id_or_identifier: NonNegativeInt | str,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
        is_archived: bool | None = None,
    ) -> JobTemplateBaseDetailedView:
        """
        Update a job template.

        Args:
            id_or_identifier: The ID or identifier of the job template.
            name: The name of the job template.
            identifier: The identifier of the job template.
            description: The description of the job template.
            template_vars: The template variables.
            is_archived: Whether the job template is archived.

        Returns:
            The detailed view of the updated job template.
        """
        data = filter_null_out(
            dict(
                name=name,
                identifier=identifier,
                description=description,
                template_vars=template_vars,
                is_archived=is_archived,
            )
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="PUT",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobTemplateBaseDetailedView)
        )

    @cached_property
    def files(self) -> Files:
        """
        Get the Files instance.

        Returns:
            The Files instance.
        """
        return Files(client=self.client, request_handler_cls=self.request_handler_cls)
