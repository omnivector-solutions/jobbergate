"""
Provide tool functions for working with Job Submission data
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

from buzz import enforce_defined
from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.constants import FileType
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ContextProtocol, JobSubmissionCreateRequestData, JobSubmissionResponse
from jobbergate_cli.subapps.job_scripts.tools import download_job_script_files
from jobbergate_core.tools.sbatch import SubmissionHandler, inject_sbatch_params


def _normalize_error_output(output: object) -> str:
    """Normalize different error payload types to display-friendly text."""
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode(errors="replace").strip()
    return str(output).strip()


def _extract_sbatch_failure_reason(err: Exception) -> str:
    """Extract an informative reason from known exception attributes."""
    parts: list[str] = []
    for attr in ("stderr", "stdout", "output"):
        value = _normalize_error_output(getattr(err, attr, None))
        if value:
            parts.append(value)

    fallback = _normalize_error_output(err)
    if fallback:
        parts.append(fallback)

    deduplicated: list[str] = []
    for part in parts:
        if part and part not in deduplicated:
            deduplicated.append(part)

    if not deduplicated:
        return "Unknown sbatch error"

    return " | ".join(" ".join(part.split()) for part in deduplicated)


def _suggest_resolution_from_reason(reason: str) -> str:
    """Provide a short actionable suggestion based on common Slurm failure patterns."""
    normalized_reason = reason.lower()
    if "memory" in normalized_reason or "mem=" in normalized_reason:
        return "Suggestion: Lower requested memory or choose a queue/node type with higher memory limits."
    if "cpu" in normalized_reason or "cpus" in normalized_reason:
        return "Suggestion: Lower requested CPU count or choose resources that match your CPU request."
    if "qos" in normalized_reason:
        return "Suggestion: Verify the requested QoS is available for your account and cluster."
    if "partition" in normalized_reason:
        return "Suggestion: Verify the requested partition name exists on the target cluster."
    if "constraint" in normalized_reason or "feature" in normalized_reason or "node" in normalized_reason:
        return "Suggestion: Adjust node/feature constraints to match available cluster resources."
    return "Suggestion: Verify requested Slurm resources and cluster parameters before retrying."


def _format_sbatch_submission_error(err: Exception) -> str:
    """Build a concise and actionable end-user message for sbatch submission failures."""
    reason = _extract_sbatch_failure_reason(err)
    suggestion = _suggest_resolution_from_reason(reason)
    return f"Slurm rejected the job submission.\nReason: {reason}\n{suggestion}"


def _map_cluster_name(
    jg_ctx: ContextProtocol,
    base_cluster_name: str,
) -> str:
    """
    Injects the organization name into the cluster name for multi-tenancy mode.

    If the organization is undefined (multi-tenancy is disabled) or the cluster_name already includes the
    organization_id, use the base_cluster_name.
    """
    org_id = jg_ctx.authentication_handler.get_identity_data().organization_id
    if org_id is None or base_cluster_name.endswith(org_id):
        return base_cluster_name

    return f"{base_cluster_name}-{org_id}"


@dataclass
class JobSubmissionABC(ABC):
    """
    A dataclass representing a job submission for Jobbergate.

    Args:
        jg_ctx: The JobbergateContext. Used to retrieve the client for requests and the email of the submitting user.
        job_script_id: The ``id`` of the Job Script to submit to Slurm.
        name: The name to attach to the Job Submission.
        description: An optional description that may be added to the Job Submission.
        cluster_name: An optional cluster_name for the cluster where the job should be executed.
            If left off, it will default to the DEFAULT_CLUSTER_NAME from the settings.
            If no default is set, an exception will be raised.
        execution_directory: An optional directory where the job should be executed. If provided as a
            relative path, it will be constructed as an absolute path relative to
            the current working directory.
        download: A flag indicating whether the job script files should be downloaded to the execution directory.
        sbatch_arguments: An optional list of arguments to pass to inject into the job script.
    """

    jg_ctx: ContextProtocol
    job_script_id: int
    name: str
    execution_directory: Path | None = None
    cluster_name: str | None = None
    download: bool = False
    description: Optional[str] = None
    sbatch_arguments: Optional[list[str]] = None

    def __post_init__(self):
        """Post-init hook to ensure that the cluster_name and execution_directory are set correctly."""
        if not self.cluster_name:
            self.cluster_name = settings.DEFAULT_CLUSTER_NAME
        if self.cluster_name is None:
            raise ValueError("No cluster name supplied and no default exists. Cannot submit to an unknown cluster!")
        self.cluster_name = _map_cluster_name(self.jg_ctx, self.cluster_name)

        if self.execution_directory is None:
            self.execution_directory = Path.cwd()
        if not self.execution_directory.is_absolute():
            self.execution_directory = self.execution_directory.resolve()

    @abstractmethod
    def process_submission(self):
        """Process the job submission. This method should be overridden by subclasses."""
        pass

    def get_request_data(self) -> JobSubmissionCreateRequestData:
        """Return the data to be used in the POST request to the API."""
        return JobSubmissionCreateRequestData(
            name=self.name,
            description=self.description,
            job_script_id=self.job_script_id,
            cluster_name=self.cluster_name,
            execution_directory=self.execution_directory,
            sbatch_arguments=self.sbatch_arguments,
        )

    def make_post_request(self, job_submission_data: JobSubmissionCreateRequestData) -> JobSubmissionResponse:
        """Make the POST request to the API to create the job submission."""
        return cast(
            JobSubmissionResponse,
            make_request(
                self.jg_ctx.client,
                "/jobbergate/job-submissions",
                "POST",
                expected_status=201,
                abort_message="Couldn't create job submission",
                support=True,
                request_model=job_submission_data,
                response_model_cls=JobSubmissionResponse,
            ),
        )

    def run(self) -> JobSubmissionResponse:
        """Run all required steps to create the job submission."""
        self.process_submission()
        job_submission_data = self.get_request_data()
        return self.make_post_request(job_submission_data)


class RemoteJobSubmission(JobSubmissionABC):
    def process_submission(self):
        """Process the job submission in remote mode."""
        logger.info("Creating job submission in remote mode")
        if self.download:
            download_job_script_files(self.job_script_id, self.jg_ctx, self.execution_directory)


class OnsiteJobSubmission(JobSubmissionABC):
    def process_submission(self):
        """Process the job submission in on-site mode."""
        logger.info("Creating job submission in on-site mode")
        if settings.SBATCH_PATH is None:
            raise Abort(
                "SBATCH_PATH most be set for onsite submissions",
                subject="Configuration Error",
                support=True,
            )

        job_script_files = download_job_script_files(self.job_script_id, self.jg_ctx, self.execution_directory)

        entrypoint_file = [f for f in job_script_files if f.file_type == FileType.ENTRYPOINT]

        Abort.require_condition(
            len(entrypoint_file) == 1,
            f"There should be exactly one entrypoint file in the parent job script, got {len(entrypoint_file)}",
            raise_kwargs={"subject": "Job Script Error"},
        )
        job_script_path = self.execution_directory / entrypoint_file[0].filename

        self.inject_sbatch_params(job_script_path)

        try:
            sbatch_handler = SubmissionHandler(
                sbatch_path=settings.SBATCH_PATH,
                submission_directory=self.execution_directory,
            )
            slurm_id = sbatch_handler.submit_job(job_script_path)
        except Exception as e:
            raise Abort(
                _format_sbatch_submission_error(e),
                subject="Slurm Submission Error",
                support=True,
                log_message=f"On-site submission failed: {e}",
            ) from e
        self.slurm_job_id = slurm_id

    def inject_sbatch_params(self, job_script_path: Path):
        """Inject sbatch parameters into the job script."""
        if not self.sbatch_arguments:
            return
        job_script_content = job_script_path.read_text()
        job_script_content = inject_sbatch_params(
            job_script_content, self.sbatch_arguments, "Injected at submission time by Jobbergate CLI"
        )
        job_script_path.write_text(job_script_content)

    def get_request_data(self) -> JobSubmissionCreateRequestData:
        """Return the data to be used in the POST request to the API."""
        data = super().get_request_data()
        data.slurm_job_id = enforce_defined(
            getattr(self, "slurm_job_id", None),
            "Slurm job id not found, on-site submission failed",
            raise_exc_class=Abort,
            raise_kwargs={
                "subject": "Slurm Submission Error",
                "support": True,
            },
        )
        return data


def job_submissions_factory(
    jg_ctx: ContextProtocol,
    job_script_id: int,
    name: str,
    execution_directory: Path | None = None,
    cluster_name: str | None = None,
    download: bool = False,
    description: Optional[str] = None,
    sbatch_arguments: Optional[list[str]] = None,
) -> JobSubmissionABC:
    """Job submission factory function. Returns the correct job submission class based on the current mode."""
    if settings.is_onsite_mode:
        return OnsiteJobSubmission(
            jg_ctx=jg_ctx,
            job_script_id=job_script_id,
            name=name,
            execution_directory=execution_directory,
            cluster_name=cluster_name,
            download=download,
            description=description,
            sbatch_arguments=sbatch_arguments,
        )
    return RemoteJobSubmission(
        jg_ctx=jg_ctx,
        job_script_id=job_script_id,
        name=name,
        execution_directory=execution_directory,
        cluster_name=cluster_name,
        download=download,
        description=description,
        sbatch_arguments=sbatch_arguments,
    )


def fetch_job_submission_data(
    jg_ctx: ContextProtocol,
    job_submission_id: int,
) -> JobSubmissionResponse:
    """
    Retrieve a job submission from the API by ``id``
    """

    return cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-submissions/{job_submission_id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job submission {job_submission_id} from API",
            support=True,
            response_model_cls=JobSubmissionResponse,
        ),
    )
