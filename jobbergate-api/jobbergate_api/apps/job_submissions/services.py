"""Services for the job_submissions resource, including module specific business logic."""

from typing import Any

from buzz import enforce_defined, require_condition
from fastapi import status
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import CrudModel, CrudService, ServiceError


class JobSubmissionService(CrudService):
    """
    Provide a CrudService that overloads the list query builder.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        user_email: str | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        eager_join: bool = False,
        innerjoin: bool = False,
        filter_slurm_job_ids: list[int] | None = None,
        **additional_filters,
    ) -> Select:
        """
        List all job_script_templates.
        """
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            user_email=user_email,
            search=search,
            sort_field=sort_field,
            include_archived=True,
            eager_join=eager_join,
            innerjoin=innerjoin,
            **additional_filters,
        )
        if filter_slurm_job_ids:
            query = query.where(JobSubmission.slurm_job_id.in_(filter_slurm_job_ids))
        return query

    async def get_ensure_client_id(self, locator: Any, requester_client_id: str | None) -> CrudModel:
        """
        Assert client_id of an entity and raise 403 exception with message on failure.
        """
        enforce_defined(
            requester_client_id,
            "Access token does not contain a client_id",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_400_BAD_REQUEST),
        )

        entity = await self.get(locator)

        require_condition(
            entity.client_id == requester_client_id,
            f"Client {requester_client_id} does not own {self.name} by {locator}.",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_403_FORBIDDEN),
        )

        return entity


crud_service = JobSubmissionService(model_type=JobSubmission, parent_model_link=JobSubmission.job_script)
