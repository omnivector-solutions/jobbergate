from datetime import datetime
from enum import Enum
from functools import cached_property, partial
from pathlib import Path
from typing import Any, ClassVar, Self

from pydantic import ConfigDict, Field, validate_call
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.schemas import (
    JobTemplateDetailedView,
    JobTemplateListView,
    ListResponseEnvelope,
    TemplateFileDetailedView,
    WorkflowFileDetailedView,
)
from jobbergate_core.tools.requests import Client, RequestHandler


class FileType(str, Enum):
    """File type enum."""

    ENTRYPOINT = "ENTRYPOINT"
    SUPPORT = "SUPPORT"


class RequestClientBinder:
    def bind(self, client: Client) -> Self:
        self._request_client = client
        return self

    def unbind(self) -> None:
        delattr(self, "_request_client")

    @property
    def request_client(self) -> Client:
        client = getattr(self, "_request_client", None)
        if client is None:
            raise ValueError("The request client has not been bound")
        return client


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class TemplateFileClient(RequestClientBinder):
    parent_id: int
    filename: str
    file_type: FileType
    created_at: datetime
    updated_at: datetime

    @classmethod
    @validate_call
    def upsert(
        cls, id_or_identifier: int | str, file_type: FileType, file_path: Path, request_client: Client
    ) -> "TemplateFileClient":
        with file_path.open("rb") as file:
            response = RequestHandler(
                client=request_client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{file_type.value}",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (file_path.name, file, "text/plain")},
                ),
            )
        data = response.raise_for_status().check_status_code(200).to_json()
        return cls(**data).bind(request_client)

    @validate_call
    def delete(self) -> None:
        (
            RequestHandler(
                client=self.request_client,
                url_path=f"/jobbergate/job-script-templates/{self.parent_id}/upload/template/{self.filename}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(200)
        )

    @validate_call
    def update(self, filename: str | None = None, file_type=FileType | None) -> "TemplateFileClient":
        if filename is None and file_type is None:
            raise ValueError("At least one of 'filename' or 'file_type' must be set")
        data = dict(filename=filename, file_type=file_type)
        response = RequestHandler(
            client=self.request_client,
            url_path=f"/jobbergate/job-script-templates/{self.parent_id}/upload/template/{self.filename}",
            method="PUT",
            request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
        )
        data = response.raise_for_status().check_status_code(200).to_json()
        return self.__class__(**data).bind(self.request_client)

    @validate_call
    def upload(self, file_path: Path) -> "TemplateFileClient":
        with file_path.open("rb") as file:
            response = RequestHandler(
                client=self.request_client,
                url_path=f"/jobbergate/job-script-templates/{self.parent_id}/upload/template/{self.file_type.value}",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (self.filename, file, "text/plain")},
                ),
            )
        data = response.raise_for_status().check_status_code(200).to_json()
        return self.__class__(**data).bind(self.request_client)

    @validate_call
    def download(self, directory: Path = Path.cwd()) -> Path:
        output_path = directory / self.filename
        (
            RequestHandler(
                client=self.request_client,
                url_path=f"/jobbergate/job-script-templates/{self.parent_id}/upload/template/{self.filename}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(200)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class TemplateFiles:
    client: Client

    @validate_call
    def upsert(self, id_or_identifier: int | str, file_type: FileType, file_path: Path) -> TemplateFileDetailedView:
        with file_path.open("rb") as file:
            response = RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{file_type.value}",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (file_path.name, file, "text/plain")},
                ),
            )
        return response.raise_for_status().check_status_code(200).to_model(TemplateFileDetailedView)

    @validate_call
    def delete(self, id_or_identifier: int | str, filename: str) -> None:
        (
            RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{filename}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(200)
        )

    @validate_call
    def download(self, id_or_identifier: int | str, filename: str, directory: Path = Path.cwd()) -> Path:
        output_path = directory / filename
        (
            RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/template/{filename}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(200)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class WorkflowFiles:
    client: Client

    @validate_call
    def upsert(
        self,
        id_or_identifier: int | str,
        file_path: Path,
        runtime_config: dict[str, Any] | None = None,
    ) -> WorkflowFileDetailedView:
        with file_path.open("rb") as file:
            response = RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (file_path.name, file, "text/plain")},
                    data={"runtime_config": runtime_config},
                ),
            )
        return response.raise_for_status().check_status_code(200).to_model(WorkflowFileDetailedView)

    @validate_call
    def delete(self, id_or_identifier: int | str) -> None:
        (
            RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(200)
        )

    @validate_call
    def download(self, id_or_identifier: int | str, directory: Path = Path.cwd()) -> Path:
        output_path = directory / "jobbergate.py"
        (
            RequestHandler(
                client=self.client,
                url_path=f"/jobbergate/job-script-templates/{id_or_identifier}/upload/workflow",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(200)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Files:
    client: Client

    @cached_property
    def template(self) -> TemplateFiles:
        return TemplateFiles(client=self.client)

    @cached_property
    def workflow(self) -> WorkflowFiles:
        return WorkflowFiles(client=self.client)


@dataclass(kw_only=True, config=ConfigDict(arbitrary_types_allowed=True))
class BaseJobTemplate:
    client: Client

    name: str | None = None
    id: int | None = None
    identifier: str | None = None
    description: str | None = None
    template_vars: dict[str, Any] | None = None
    is_archived: bool | None = None

    base_path: ClassVar[str] = "/jobbergate/job-script-templates"

    @property
    def id_or_identifier(self) -> int | str:
        if self.id is not None:
            return self.id
        elif self.identifier is not None:
            return self.identifier
        raise ValueError("Neither 'id' nor 'identifier' is set")

    @validate_call
    def clone(
        self,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> JobTemplateDetailedView:
        data = dict(name=name, identifier=identifier, description=description, template_vars=template_vars)
        return (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/clone/{self.id_or_identifier}",
                method="POST",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(201)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def create(self) -> JobTemplateDetailedView:
        if self.name is None:
            raise ValueError("The 'name' attribute must be set")
        data = dict(
            name=self.name, identifier=self.identifier, description=self.description, template_vars=self.template_vars
        )
        return (
            RequestHandler(
                client=self.client,
                url_path=self.base_path,
                method="POST",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(201)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def delete(self) -> None:
        (
            RequestHandler(client=self.client, url_path=f"{self.base_path}/{self.id_or_identifier}", method="DELETE")
            .raise_for_status()
            .check_status_code(204)
        )

    @validate_call
    def get_details(self) -> JobTemplateDetailedView:
        return (
            RequestHandler(client=self.client, url_path=f"{self.base_path}/{self.id_or_identifier}", method="GET")
            .raise_for_status()
            .check_status_code(200)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def update(
        self,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
        is_archived: bool | None = None,
    ) -> JobTemplateDetailedView:
        data = dict(
            name=name,
            identifier=identifier,
            description=description,
            template_vars=template_vars,
            is_archived=is_archived,
        )
        return (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/{self.id_or_identifier}",
                method="PUT",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(200)
            .to_model(JobTemplateDetailedView)
        )


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class JobTemplates:
    client: Client

    base_path: ClassVar[str] = "/jobbergate/job-script-templates"

    @validate_call
    def clone(
        self,
        base_id_or_identifier: int | str,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> JobTemplateDetailedView:
        data = dict(name=name, identifier=identifier, description=description, template_vars=template_vars)
        return (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/clone/{base_id_or_identifier}",
                method="POST",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(201)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def create(
        self,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> JobTemplateDetailedView:
        data = dict(name=name, identifier=identifier, description=description, template_vars=template_vars)
        return (
            RequestHandler(
                client=self.client,
                url_path=self.base_path,
                method="POST",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(201)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def delete(self, id_or_identifier: int | str) -> None:
        (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(204)
        )

    @validate_call
    def get_one(self, id_or_identifier: int | str) -> JobTemplateDetailedView:
        return (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(200)
            .to_model(JobTemplateDetailedView)
        )

    @validate_call
    def list(
        self,
        include_null_identifier: bool = False,
        sort_ascending: bool = True,
        user_only: bool = False,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = False,
        include_parent: bool = False,
        size: int = Field(50, ge=1, le=100),
        page: int = Field(1, ge=1),
    ) -> ListResponseEnvelope[JobTemplateListView]:
        params = dict(
            include_null_identifier=include_null_identifier,
            sort_ascending=sort_ascending,
            user_only=user_only,
            search=search,
            sort_field=sort_field,
            include_archived=include_archived,
            include_parent=include_parent,
            size=size,
            page=page,
        )
        result = (
            RequestHandler(
                client=self.client,
                url_path=self.base_path,
                method="GET",
                request_kwargs=dict(params={k: v for k, v in params.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(200)
            .to_model(ListResponseEnvelope[JobTemplateListView])
        )
        return result

    @validate_call
    def update(
        self,
        id_or_identifier: int | str,
        *,
        name: str | None = None,
        identifier: str | None = None,
        description: str | None = None,
        template_vars: dict[str, Any] | None = None,
        is_archived: bool | None = None,
    ) -> JobTemplateDetailedView:
        data = dict(
            name=name,
            identifier=identifier,
            description=description,
            template_vars=template_vars,
            is_archived=is_archived,
        )
        return (
            RequestHandler(
                client=self.client,
                url_path=f"{self.base_path}/{id_or_identifier}",
                method="PUT",
                request_kwargs=dict(data={k: v for k, v in data.items() if v is not None}),
            )
            .raise_for_status()
            .check_status_code(200)
            .to_model(JobTemplateDetailedView)
        )

    @cached_property
    def files(self) -> Files:
        return Files(client=self.client)
