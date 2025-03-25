"""Services for the job_submissions resource, including module specific business logic."""

from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import CrudService


class JobSubmissionService(CrudService):
    """
    Provide a CrudService that overloads the list query builder.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_files: bool = False,
        include_parent: bool = False,
        filter_slurm_job_ids: list[int] | None = None,
        **additional_filters,
    ) -> Select:
        """
        List all job_script_templates.
        """
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            search=search,
            sort_field=sort_field,
            include_archived=include_archived,
            include_files=include_files,
            include_parent=include_parent,
            **additional_filters,
        )
        if filter_slurm_job_ids:
            query = query.where(JobSubmission.slurm_job_id.in_(filter_slurm_job_ids))
        return query


class JobProgressService(CrudService):
    """
    Provide a CrudService that overloads the list query builder.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_files: bool = False,
        include_parent: bool = False,
        **additional_filters,
    ) -> Select:
        """
        List all entries in the job_progress table for a given job_submission_id.
        """
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            sort_field=sort_field,
            **additional_filters,
        )
        return query
