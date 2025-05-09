"""Services for the job_script_templates resource, including module specific business logic."""

from typing import Any

from buzz import require_condition
from fastapi import status
from loguru import logger
from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.services import AutoCleanResponse, CrudModel, CrudService, FileService, ServiceError
from jobbergate_api.config import settings


class JobScriptTemplateService(CrudService):
    """
    Provide a CrudService that overloads the list query builder and locator logic.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_files: bool = False,
        include_parent: bool = False,
        include_null_identifier: bool = True,
        **additional_filters,
    ) -> Select:
        """List all job_script_templates."""
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            search=search,
            sort_field=sort_field,
            include_archived=include_archived,
            include_files=include_files,
            include_parent=include_parent,
            **additional_filters,
        )
        if not include_null_identifier:
            query = query.where(not_(JobScriptTemplate.identifier.is_(None)))
        return query

    async def create(self, **incoming_data) -> CrudModel:
        """
        Add a new row for the model to the database.
        """
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().create(**incoming_data)

    async def update(self, locator: Any, **incoming_data) -> CrudModel:
        """
        Update a row by locator with supplied data.
        """
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().update(locator, **incoming_data)

    def locate_where_clause(self, id_or_identifier: Any) -> Any:
        """
        Locate an instance using the id or identifier field.
        """
        if isinstance(id_or_identifier, str):
            return JobScriptTemplate.identifier == id_or_identifier
        elif isinstance(id_or_identifier, int):
            return JobScriptTemplate.id == id_or_identifier
        else:
            raise ValueError("id_or_identifier must be a string or integer")

    def validate_identifier(self, identifier: str | None) -> None:
        """
        Validate that the identifier is not an empty string nor composed only by digits.

        Raise a ServiceError with status code 422 if the validation fails.

        Many of the job-script-template endpoints use the id or identifier interchangeably
        as a path parameter. With that, we need to ensure that the identifier is
        not a number, as that would be identified as id.
        """
        if identifier is not None:
            require_condition(
                identifier.strip() and not identifier.isdigit(),
                "Identifier on {} can not be a empty string nor be composed only by digits. Got {}".format(
                    self.name, identifier
                ),
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
            )

    async def clean_unused_entries(self) -> AutoCleanResponse:
        """
        Automatically clean unused job script templates depending on a threshold.

        Based on the last time each job script template was updated or used to create a job script,
        this will archive job script templates that were unarchived and delete job script templates
        that were archived.
        """
        result = AutoCleanResponse(archived=set(), deleted=set())

        if settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_DELETE is not None:
            days_to_delete = settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_DELETE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_delete).naive()
            subquery_unused_job_script_templates = select(self.model_type.id).where(
                self.model_type.is_archived.is_(True), self.model_type.updated_at < threshold
            )
            subquery_recent_child = (
                select(JobScript.parent_template_id)
                .where(JobScript.parent_template_id.in_(subquery_unused_job_script_templates))
                .group_by(JobScript.parent_template_id)
                .having(func.max(JobScript.created_at) >= threshold)
            )

            delete_query = (
                delete(self.model_type)  # type: ignore
                .where(
                    self.model_type.id.in_(subquery_unused_job_script_templates),
                    ~self.model_type.id.in_(subquery_recent_child),
                )
                .returning(self.model_type.id)
            )
            deleted = await self.session.execute(delete_query)
            result.deleted.update(row[0] for row in deleted.all())
        logger.debug(f"Job script templates deleted: {result.deleted}")

        if settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_ARCHIVE is not None:
            days_to_archive = settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_ARCHIVE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_archive).naive()
            subquery_unused_job_script_templates = select(self.model_type.id).where(
                self.model_type.is_archived.is_(False), self.model_type.updated_at < threshold
            )
            subquery_recent_child = (
                select(JobScript.parent_template_id)
                .where(JobScript.parent_template_id.in_(subquery_unused_job_script_templates))
                .group_by(JobScript.parent_template_id)
                .having(func.max(JobScript.created_at) >= threshold)
            )

            update_query = (
                update(self.model_type)  # type: ignore
                .where(
                    self.model_type.id.in_(subquery_unused_job_script_templates),
                    ~self.model_type.id.in_(subquery_recent_child),
                )
                .values(is_archived=True)
                .returning(self.model_type.id)
            )
            archived = await self.session.execute(update_query)
            result.archived.update(row[0] for row in archived.all())
        logger.debug(f"Job script templates marked as archived: {result.archived}")

        return result


class JobScriptTemplateFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes errors with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptTemplateFile"
        error: Value of type variable "FileModel" of "FileService" cannot be "WorkflowFile"
    """
