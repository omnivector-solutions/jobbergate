from pydantic import NonNegativeInt
from jobbergate_core.sdk.job_scripts.schemas import JobScriptBaseView
from jobbergate_core.sdk.job_submissions.constants import JobSubmissionStatus
from jobbergate_core.sdk.schemas import TableResource


class JobSubmissionBaseView(TableResource):
    """
    Base model to match database for the JobSubmission resource.

    Omits parent relationship.
    """

    job_script_id: NonNegativeInt | None = None
    slurm_job_id: NonNegativeInt | None = None
    client_id: str
    status: JobSubmissionStatus
    slurm_job_state: str | None = None
    cloned_from_id: NonNegativeInt | None = None


class JobSubmissionListView(JobSubmissionBaseView):
    """Model to match database for the JobSubmission resource.

    Notice files are omitted. Parent job-script can be included."""

    job_script: JobScriptBaseView | None = None


class JobSubmissionDetailedView(JobSubmissionBaseView):
    """Model to match database for the JobSubmission resource."""

    execution_directory: str | None = None
    report_message: str | None = None
    slurm_job_info: str | None = None
    sbatch_arguments: list[str] | None = None
