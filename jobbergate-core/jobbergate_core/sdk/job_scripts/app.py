"""
SDK module to interact with job scripts.
"""

from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Type

from httpx import codes
from pydantic import ConfigDict, NonNegativeInt, PositiveInt, validate_call
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.constants import FileType
from jobbergate_core.sdk.job_scripts.schemas import (
    JobScriptBaseView,
    JobScriptDetailedView,
    JobScriptFileDetailedView,
    JobScriptListView,
)
from jobbergate_core.sdk.schemas import ListResponseEnvelope
from jobbergate_core.sdk.utils import filter_null_out
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class JobScriptFiles:
    """
    SDK class to interact with job script files.
    """

    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @validate_call
    def upsert(self, id: NonNegativeInt, file_type: FileType, file_path: Path) -> JobScriptFileDetailedView:
        """
        Upload or update a job script file.

        Args:
            id: The ID of the job script.
            file_type: The type of the file.
            file_path: The path to the file to be uploaded.

        Returns:
            The detailed view of the job script file.
        """
        with file_path.open("rb") as file:
            response = self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-scripts/{id}/upload/{file_type.value}",
                method="PUT",
                request_kwargs=dict(
                    files={"upload_file": (file_path.name, file, "text/plain")},
                ),
            )
        return response.raise_for_status().check_status_code(codes.OK).to_model(JobScriptFileDetailedView)

    @validate_call
    def delete(self, id: NonNegativeInt, filename: str) -> None:
        """
        Delete a job script file.

        Args:
            id: The ID of the job script.
            filename: The name of the file to be deleted.
        """
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-scripts/{id}/upload/{filename}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
        )

    @validate_call
    def download(self, id: NonNegativeInt, filename: str, directory: Path = Path.cwd()) -> Path:
        """
        Download a job script file.

        Args:
            id: The ID of the job script.
            filename: The name of the file to be downloaded.
            directory: The directory where the file will be saved.

        Returns:
            The path to the downloaded file.
        """
        output_path = (directory / filename).resolve()
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"/jobbergate/job-scripts/{id}/upload/{filename}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_file(output_path)
        )
        return output_path


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class JobScripts:
    """
    SDK class to interact with job scripts.
    """

    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    base_path: ClassVar[str] = "/jobbergate/job-scripts"

    @validate_call
    def clone(
        self,
        base_id: NonNegativeInt,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> JobScriptDetailedView:
        """
        Clone a job script.

        Args:
            base_id: The ID of the base job script.
            name: The name of the new job script.
            description: The description of the new job script.

        Returns:
            The detailed view of the cloned job script.
        """
        data = filter_null_out(dict(name=name, description=description))
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/clone/{base_id}",
                method="POST",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobScriptDetailedView)
        )

    @validate_call
    def create(
        self,
        name: str,
        description: str | None = None,
    ) -> JobScriptBaseView:
        """
        Create a stand alone job script. Use file upload to add files.

        Args:
            name: The name of the job script.
            identifier: The identifier of the job script.
            description: The description of the job script.
            template_vars: The template variables.

        Returns:
            The detailed view of the created job script.
        """
        data = filter_null_out(dict(name=name, description=description))
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="POST",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobScriptBaseView)
        )

    @validate_call
    def delete(self, id: NonNegativeInt) -> None:
        """
        Delete a job script.

        Args:
            id: The ID of the job script.
        """
        (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id}",
                method="DELETE",
            )
            .raise_for_status()
            .check_status_code(codes.NO_CONTENT)
        )

    @validate_call
    def get_list(
        self,
        sort_ascending: bool = True,
        user_only: bool = False,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = False,
        include_parent: bool = False,
        from_job_script_template_id: NonNegativeInt | None = None,
        size: PositiveInt = 50,
        page: PositiveInt = 1,
    ) -> ListResponseEnvelope[JobScriptListView]:
        """
        List job scripts.

        Args:
            include_null_identifier: Whether to include scripts with null identifiers.
            sort_ascending: Whether to sort in ascending order.
            user_only: Whether to include only user-specific scripts.
            search: The search query.
            sort_field: The field to sort by.
            include_archived: Whether to include archived scripts.
            size: The number of scripts per page.
            page: The page number.

        Returns:
            The list response envelope containing job script list views.
        """
        params = filter_null_out(
            dict(
                sort_ascending=sort_ascending,
                user_only=user_only,
                search=search,
                sort_field=sort_field,
                include_archived=include_archived,
                include_parent=include_parent,
                from_job_script_template_id=from_job_script_template_id,
                size=size,
                page=page,
            )
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="GET",
                request_kwargs=dict(params=params),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(ListResponseEnvelope[JobScriptListView])
        )

    @validate_call
    def get_one(self, id: NonNegativeInt) -> JobScriptDetailedView:
        """
        Get a single job script.

        Args:
            id: The ID of the job script.

        Returns:
            The detailed view of the job script.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobScriptDetailedView)
        )

    @validate_call
    def update(
        self,
        id: NonNegativeInt,
        *,
        name: str | None = None,
        description: str | None = None,
        is_archived: bool | None = None,
    ) -> JobScriptBaseView:
        """
        Update a job script.

        Args:
            id: The ID of the job script.
            name: The name of the job script.
            identifier: The identifier of the job script.
            description: The description of the job script.
            template_vars: The template variables.
            is_archived: Whether the job script is archived.

        Returns:
            The detailed view of the updated job script.
        """
        data = filter_null_out(
            dict(
                name=name,
                description=description,
                is_archived=is_archived,
            )
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id}",
                method="PUT",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobScriptBaseView)
        )

    @validate_call
    def render_from_template(
        self,
        id_or_identifier: NonNegativeInt | str,
        name: str,
        *,
        template_output_name_mapping: dict[str, str],
        param_dict: dict[str, Any],
        description: str | None = None,
        sbatch_params: list[str] | None = None,
    ) -> JobScriptDetailedView:
        """
        Render a job script from a template.

        Args:
            id_or_identifier: The ID or identifier of the base job script template.
            name: The name of the new job script.
            template_output_name_mapping: The mapping of template output names to new names.
            param_dict: The render parameters dictionary.
            description: The description of the new job script.
            sbatch_params: The sbatch parameters.

        Returns:
            The detailed view of the rendered job script.
        """
        data = dict(
            create_request=filter_null_out(dict(name=name, description=description)),
            render_request=filter_null_out(
                dict(
                    template_output_name_mapping=template_output_name_mapping,
                    sbatch_params=sbatch_params,
                    param_dict=param_dict,
                )
            ),
        )
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/render-from-template/{id_or_identifier}",
                method="POST",
                request_kwargs=dict(data=data),
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobScriptDetailedView)
        )

    @cached_property
    def files(self) -> JobScriptFiles:
        """
        Get the JobScriptFiles instance.

        Returns:
            The JobScriptFiles instance.
        """
        return JobScriptFiles(client=self.client, request_handler_cls=self.request_handler_cls)
