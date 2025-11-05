"""Services for the job_scripts resource, including module specific business logic."""

from typing import Any

from buzz import enforce_defined, require_condition
from fastapi import UploadFile, status
from loguru import logger
from pendulum.datetime import DateTime as PendulumDateTime
from pydantic import AnyUrl
from sqlalchemy import delete, func, select, update

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.services import AutoCleanResponse, CrudService, FileModel, FileService, ServiceError
from sqlalchemy.sql.expression import Select
from jobbergate_api.config import settings


class JobScriptCrudService(CrudService):
    """
    Provide an empty derived class of CrudService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "CrudModel" of "CrudService" cannot be "JobScript"
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
        """List all job_scripts with optional exclusion of rows missing identifier."""
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
            query = query.where(self.model_type.identifier.is_not(None))
        return query

    async def create(self, **incoming_data) -> JobScript:
        """Validate identifier before creating."""
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().create(**incoming_data)

    async def update(self, locator: Any, **incoming_data) -> JobScript:
        """Validate identifier before updating."""
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().update(locator, **incoming_data)

    def locate_where_clause(self, id_or_identifier: Any) -> Any:
        """Locate an instance using the id or identifier field."""
        if isinstance(id_or_identifier, str):
            return self.model_type.identifier == id_or_identifier
        elif isinstance(id_or_identifier, int):
            return self.model_type.id == id_or_identifier
        else:
            raise ValueError("id_or_identifier must be a string or integer")

    def validate_identifier(self, identifier: str | None) -> None:
        """Validate that the identifier is not an empty string nor composed only by digits."""
        if identifier is not None:
            require_condition(
                identifier.strip() and not identifier.isdigit(),
                "Identifier on {} can not be a empty string nor be composed only by digits. Got {}".format(
                    self.name, identifier
                ),
                raise_exc_class=ServiceError,
                raise_kwargs={"status_code": status.HTTP_422_UNPROCESSABLE_ENTITY},
            )

    async def delete(self, locator: Any) -> None:
        """
        Extend delete a row by locator.

        Orphaned job-scripts are now allowed on Jobbergate. However, the agent
        relies on them to submit jobs after requesting GET /agent/pending.
        This creates a race condition and errors occur when a job-script is
        deleted before the agent handles its submissions.

        To avoid this, they are marked as reject in this scenario.
        """
        query = (
            update(JobSubmission)  # type: ignore
            .where(JobSubmission.job_script_id == locator)
            .where(JobSubmission.status == JobSubmissionStatus.CREATED)
            .values(
                status=JobSubmissionStatus.REJECTED,
                report_message="Parent job script was deleted before the submission.",
            )
        )
        await self.session.execute(query)
        await super().delete(locator)

    async def clean_unused_entries(self) -> AutoCleanResponse:
        """
        Automatically clean unused job scripts depending on a threshold.

        Based on the last time each job script was updated or used to create a job submission,
        this will archive job scripts that were unarchived and delete job scripts that were archived.
        """
        result = AutoCleanResponse(archived=set(), deleted=set())

        if settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE is not None:
            days_to_delete = settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_delete).naive()
            subquery_unused_job_script = select(self.model_type.id).where(
                self.model_type.is_archived.is_(True), self.model_type.updated_at < threshold
            )
            subquery_recent_child = (
                select(JobSubmission.job_script_id)
                .where(JobSubmission.job_script_id.in_(subquery_unused_job_script))
                .group_by(JobSubmission.job_script_id)
                .having(func.max(JobSubmission.created_at) >= threshold)
            )

            delete_query = (
                delete(self.model_type)  # type: ignore
                .where(
                    self.model_type.id.in_(subquery_unused_job_script),
                    ~self.model_type.id.in_(subquery_recent_child),
                )
                .returning(self.model_type.id)
            )
            deleted = await self.session.execute(delete_query)
            result.deleted.update(row[0] for row in deleted.all())
        logger.debug(f"Job scripts deleted: {result.deleted}")

        if settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE is not None:
            days_to_archive = settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE
            threshold = PendulumDateTime.utcnow().subtract(days=days_to_archive).naive()
            subquery_unused_job_script = select(self.model_type.id).where(
                self.model_type.is_archived.is_(False), self.model_type.updated_at < threshold
            )
            subquery_recent_child = (
                select(JobSubmission.job_script_id)
                .where(JobSubmission.job_script_id.in_(subquery_unused_job_script))
                .group_by(JobSubmission.job_script_id)
                .having(func.max(JobSubmission.created_at) >= threshold)
            )

            update_query = (
                update(self.model_type)  # type: ignore
                .where(
                    self.model_type.id.in_(subquery_unused_job_script),
                    ~self.model_type.id.in_(subquery_recent_child),
                )
                .values(is_archived=True)
                .returning(self.model_type.id)
            )
            archived = await self.session.execute(update_query)
            result.archived.update(row[0] for row in archived.all())
        logger.debug(f"Job scripts marked as archived: {result.archived}")

        return result


class JobScriptFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptFile"
    """

    async def upsert(
        self,
        parent_id: int,
        filename: str,
        upload_content: str | bytes | AnyUrl | UploadFile | None,
        previous_filename: str | None = None,
        **upsert_kwargs,
    ) -> FileModel:
        """
        Upsert a file instance.
        """
        file_type: str = enforce_defined(
            upsert_kwargs.get("file_type", None),
            "File type must be defined when upserting a file.",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
        )
        if file_type == FileType.ENTRYPOINT:
            await self.validate_entrypoint_file(parent_id, previous_filename or filename)
        return await super().upsert(parent_id, filename, upload_content, previous_filename, **upsert_kwargs)

    async def validate_entrypoint_file(self, parent_id: int, filename: str):
        """
        Validate that the entrypoint file is unique.
        """
        file_list = await self.find_children(parent_id)

        entry_point_names = {file.filename for file in file_list if file.file_type == FileType.ENTRYPOINT}

        no_entry_point = len(entry_point_names) == 0
        replacing_entry_point = filename in entry_point_names
        sanity_check = len(entry_point_names) <= 1

        require_condition(
            (no_entry_point or replacing_entry_point) and sanity_check,
            (
                "A job script can not have more than one entry point file. "
                "Consider deleting the existing one first. "
                "Found: {}".format(",".join(entry_point_names))
            ),
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
        )
