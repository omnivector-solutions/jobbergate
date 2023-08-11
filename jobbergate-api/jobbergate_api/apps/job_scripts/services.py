"""Services for the job_scripts resource, including module specific business logic."""
from typing import Any

from sqlalchemy import update

from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import CrudService, FileService


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


class JobScriptFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptFile"
    """


crud_service = JobScriptCrudService(model_type=JobScript)
file_service = JobScriptFileService(model_type=JobScriptFile)
