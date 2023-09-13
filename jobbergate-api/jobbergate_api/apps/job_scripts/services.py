"""Services for the job_scripts resource, including module specific business logic."""
from typing import Any, NamedTuple

from buzz import enforce_defined, require_condition
from fastapi import UploadFile, status
from loguru import logger
from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import delete, func, select, update

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import CrudService, FileModel, FileService, ServiceError
from jobbergate_api.config import settings


class AutoCleanResponse(NamedTuple):
    """
    Named tuple for the response of auto_clean_unused_job_scripts.
    """

    archived: set[int]
    deleted: set[int]


class JobScriptCrudService(CrudService):
    """
    Provide an empty derived class of CrudService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "CrudModel" of "CrudService" cannot be "JobScript"
    """

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

    async def auto_clean_unused_job_scripts(self) -> AutoCleanResponse:
        """
        Automatically clean unused job scripts depending on a threshold.

        Based on the last time each job script was updated or used to create a job submission,
        this will archived job scripts that were unarchived and delete jos script that were archived.
        """
        result = AutoCleanResponse(archived=set(), deleted=set())

        subquery = (
            select(
                JobSubmission.job_script_id,
                func.max(JobSubmission.created_at).label("last_used"),
            )  # type: ignore
            .group_by(JobSubmission.job_script_id)
            .subquery()
        )
        joined_query = (
            select(self.model_type, subquery)  # type: ignore
            .join(subquery, subquery.c.job_script_id == self.model_type.id, isouter=True)
            .subquery()
        )

        if days_to_delete := settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE:
            query = (
                delete(self.model_type)  # type: ignore
                .where(self.model_type.is_archived.is_(True))
                .where(
                    func.greatest(joined_query.c.updated_at, joined_query.c.last_used)
                    < PendulumDateTime.utcnow().subtract(days=days_to_delete).naive()
                )
                .returning(self.model_type.id)
            )
            deleted = await self.session.execute(query)
            result.deleted.update(row[0] for row in deleted.all())

        if days_to_archive := settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE:
            update_query = (
                update(self.model_type)  # type: ignore
                .where(self.model_type.is_archived.is_(False))
                .where(
                    func.greatest(joined_query.c.updated_at, joined_query.c.last_used)
                    < PendulumDateTime.utcnow().subtract(days=days_to_archive).naive()
                )
                .values(is_archived=True)
                .returning(self.model_type.id)
            )
            archived = await self.session.execute(update_query)
            result.archived.update(row[0] for row in archived.all())

        logger.debug(f"Job scripts marked as archived: {result.archived}")
        logger.debug(f"Job scripts marked as deleted: {result.deleted}")

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
        upload_content: str | bytes | UploadFile,
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
            await self.validate_entrypoint_file(parent_id, filename)
        return await super().upsert(parent_id, filename, upload_content, **upsert_kwargs)

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
