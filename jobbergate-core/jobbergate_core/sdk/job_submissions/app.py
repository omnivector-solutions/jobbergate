import time
from typing import ClassVar, Type

from httpx import codes
from pydantic import ConfigDict, NonNegativeInt, PositiveInt, validate_call
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.job_submissions.constants import JobSubmissionStatus
from jobbergate_core.sdk.job_submissions.schemas import (
    JobSubmissionDetailedView,
    JobSubmissionListView,
)
from jobbergate_core.sdk.schemas import ListResponseEnvelope
from jobbergate_core.sdk.utils import filter_null_out
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class JobSubmissions:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    base_path: ClassVar[str] = "/jobbergate/job-submissions"

    @validate_call
    def create(
        self,
        job_script_id: NonNegativeInt,
        name: str,
        *,
        description: str | None = None,
        slurm_job_id: NonNegativeInt | None = None,
        execution_directory: str | None = None,
        client_id: str | None = None,
        sbatch_arguments: list[str] | None = None,
    ) -> JobSubmissionDetailedView:
        """
        Create a job submission.

        Args:
            job_script_id: The ID of the base job script.
            name: The name of the job submission.
            description: The description of the job submission.
            slurm_job_id: The SLURM job ID.
            execution_directory: The execution directory.
            client_id: The client ID.
            sbatch_arguments: The SLURM sbatch arguments.

        Returns:
            The detailed view of the created job submission.
        """
        data = filter_null_out(
            dict(
                job_script_id=job_script_id,
                name=name,
                description=description,
                slurm_job_id=slurm_job_id,
                execution_directory=execution_directory,
                client_id=client_id,
                sbatch_arguments=sbatch_arguments,
            )
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
            .to_model(JobSubmissionDetailedView)
        )

    @validate_call
    def clone(self, id: NonNegativeInt) -> JobSubmissionDetailedView:
        """
        Clone a job submission under the CREATED status for a new run on the cluster.

        Args:
            id: The ID of the job submission to clone.

        Returns:
            The detailed view of the cloned job submission.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/clone/{id}",
                method="POST",
            )
            .raise_for_status()
            .check_status_code(codes.CREATED)
            .to_model(JobSubmissionDetailedView)
        )

    @validate_call
    def get_one(self, id: NonNegativeInt) -> JobSubmissionDetailedView:
        """
        Get a single job submission.

        Args:
            id: The ID of the job submission.

        Returns:
            The detailed view of the job submission.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{id}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobSubmissionDetailedView)
        )

    @validate_call
    def get_one_ensure_slurm_id(
        self, id: NonNegativeInt, max_retries: PositiveInt = 8, waiting_interval: PositiveInt = 15
    ) -> JobSubmissionDetailedView:
        """
        Get a single job submission and ensure that the SLURM job ID is set.

        Args:
            id: The ID of the job submission.
            max_retries: The maximum number of retry attempts.
            waiting_interval: The interval in seconds to wait between checks.

        Returns:
            The detailed view of the job submission.
        """
        for attempt in range(max_retries):
            if attempt > 0:
                time.sleep(waiting_interval)

            submission = self.get_one(id)
            if submission.slurm_job_id is not None:
                return submission
            elif submission.status == JobSubmissionStatus.REJECTED:
                raise ValueError(f"The job submission with ID {id} was rejected and does not have a SLURM job ID.")

        raise TimeoutError(f"The SLURM job ID was not set within {max_retries} retry attempts.")

    @validate_call
    def get_list(
        self,
        sort_ascending: bool = True,
        user_only: bool = False,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = False,
        include_parent: bool = False,
        slurm_job_ids: list[NonNegativeInt] | None = None,
        slurm_status: JobSubmissionStatus | None = None,
        from_job_script_id: NonNegativeInt | None = None,
        size: PositiveInt = 50,
        page: PositiveInt = 1,
    ) -> ListResponseEnvelope[JobSubmissionListView]:
        """
        List job submissions.

        Args:
            sort_ascending: Whether to sort in ascending order.
            user_only: Whether to include only user-specific submissions.
            search: The search query.
            sort_field: The field to sort by.
            include_archived: Whether to include archived submissions.
            include_parent: Whether to include parent submissions.
            slurm_job_ids: Filter by SLURM job IDs.
            slurm_status: Filter by SLURM status.
            from_job_script_id: Filter by job script ID.
            size: The number of submissions per page.
            page: The page number.

        Returns:
            The list response envelope containing job submission list views.
        """
        params = filter_null_out(
            dict(
                sort_ascending=sort_ascending,
                user_only=user_only,
                search=search,
                sort_field=sort_field,
                include_archived=include_archived,
                include_parent=include_parent,
                slurm_status=slurm_status,
                from_job_script_id=from_job_script_id,
                size=size,
                page=page,
            )
        )
        if slurm_job_ids:
            params["slurm_job_ids"] = ",".join(map(str, slurm_job_ids))

        result = (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="GET",
                request_kwargs=dict(params=params),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(ListResponseEnvelope[JobSubmissionListView])
        )
        return result

    @validate_call
    def update(
        self,
        id: NonNegativeInt,
        *,
        name: str | None = None,
        description: str | None = None,
        execution_directory: str | None = None,
        status: JobSubmissionStatus | None = None,
    ) -> JobSubmissionDetailedView:
        """
        Update a job submission.

        Args:
            id: The ID of the job submission.
            name: The name of the job submission.
            description: The description of the job submission.
            execution_directory: The execution directory.

        Returns:
            The base view of the updated job submission.
        """
        data = filter_null_out(
            dict(
                name=name,
                description=description,
                execution_directory=execution_directory,
                status=status,
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
            .to_model(JobSubmissionDetailedView)
        )

    @validate_call
    def delete(self, id: NonNegativeInt) -> None:
        """
        Delete a job submission.

        Args:
            id: The ID of the job submission.
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
    def cancel(self, id: NonNegativeInt) -> JobSubmissionDetailedView:
        """
        Cancel a job submission.

        Args:
            id: The ID of the job submission.

        Returns:
            The detailed view of the canceled job submission.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/cancel/{id}",
                method="PUT",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(JobSubmissionDetailedView)
        )
