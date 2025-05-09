"""Services for the job_submissions resource, including module specific business logic."""

from loguru import logger
from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import delete, select, update
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import AutoCleanResponse, CrudService
from jobbergate_api.config import settings


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

    async def clean_unused_entries(self) -> AutoCleanResponse:
        """
        Automatically clean unused job submissions depending on a threshold.

        Based on the last time each job submission was updated, this will archive job
        submissions that were unarchived and delete job submissions that were archived.
        """
        result = AutoCleanResponse(archived=set(), deleted=set())

        if settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE is not None:
            days_to_delete = settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_delete).naive()
            query_unused_job_submissions = select(self.model_type.id).where(
                self.model_type.is_archived.is_(True), self.model_type.updated_at < threshold
            )

            delete_query = (
                delete(self.model_type)  # type: ignore
                .where(self.model_type.id.in_(query_unused_job_submissions))
                .returning(self.model_type.id)
            )
            deleted = await self.session.execute(delete_query)
            result.deleted.update(row[0] for row in deleted.all())
        logger.debug(f"Job submissions deleted: {result.deleted}")
        logger.debug(f"{settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE=}")

        if settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE is not None:
            days_to_archive = settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_archive).naive()
            query_unused_job_submissions = select(self.model_type.id).where(
                self.model_type.is_archived.is_(False), self.model_type.updated_at < threshold
            )

            update_query = (
                update(self.model_type)  # type: ignore
                .where(self.model_type.id.in_(query_unused_job_submissions))
                .values(is_archived=True)
                .returning(self.model_type.id)
            )
            archived = await self.session.execute(update_query)
            result.archived.update(row[0] for row in archived.all())
        logger.debug(f"Job submissions marked as archived: {result.archived}")

        return result


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
