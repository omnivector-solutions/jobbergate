"""Services for the job_submissions resource, including module specific business logic."""

from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import CrudService


class JobSubmissionService(CrudService):
    def build_list_query(
        self,
        filter_slurm_job_ids: list[int] | None = None,
        eager_join: bool = False,
        **filter_kwargs,
    ) -> Select:
        """List all job_script_templates."""
        query: Select = super().build_list_query(**filter_kwargs)
        if filter_slurm_job_ids:
            query = query.where(JobSubmission.slurm_job_id.in_(filter_slurm_job_ids))
        if eager_join:
            query.options(joinedload(JobSubmission.job_script))
        return query


crud_service = JobSubmissionService(model_type=JobSubmission)
