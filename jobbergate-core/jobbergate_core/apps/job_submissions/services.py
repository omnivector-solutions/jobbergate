"""Services for job submissions."""
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

import requests

from jobbergate_core.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_core.apps.job_submissions.schemas import JobSubmissionCreateRequest, JobSubmissionResponse
from jobbergate_core.auth.handler import JobbergateAuthHandler


@dataclass
class JobSubmission:
    """Job Submission Service."""

    jobbergate_api_url: str
    jobbergate_auth: JobbergateAuthHandler

    def create(self, create_data: JobSubmissionCreateRequest) -> JobSubmissionResponse:
        """Create a new job submission."""
        response = requests.post(
            url=f"{self.jobbergate_api_url}/job-submissions",
            auth=self.jobbergate_auth,
            json=create_data.dict(exclude_unset=True, exclude_none=True),
        )
        response.raise_for_status()
        return JobSubmissionResponse(**response.json())

    def create_batch(
        self,
        create_data: Sequence[JobSubmissionCreateRequest],
        dependencies: Optional[Sequence[JobSubmissionResponse]] = None,
        dependency_type: str = "afterok",
    ) -> List[JobSubmissionResponse]:
        """Create a batch of job submissions with optional dependencies."""
        if dependencies:
            ensured_dependencies = (self.get_ensure_slurm_id(dependency) for dependency in dependencies)
            dependency = "{}:{}".format(
                dependency_type, ":".join(map(str, (v.slurm_job_id for v in ensured_dependencies)))
            )
        else:
            dependency = None

        result = []
        for data in create_data:
            if dependency:
                data.execution_parameters.dependency = dependency
            result.append(self.create(data))

        return result

    def get(self, id: int) -> JobSubmissionResponse:
        """Get a job submission by id."""
        response = requests.get(
            url=f"{self.jobbergate_api_url}/job-submissions/{id}",
            auth=self.jobbergate_auth,
        )
        response.raise_for_status()
        return JobSubmissionResponse(**response.json())

    def get_ensure_slurm_id(
        self, job_submission: JobSubmissionResponse, time_out: int = 120, waiting_interval: int = 30
    ) -> JobSubmissionResponse:
        """Get a job submission by id and ensure that the slurm_job_id is not None."""
        if job_submission.slurm_job_id is not None:
            return job_submission
        expires_at = time.time() + time_out
        while expires_at > time.time():
            response = self.get(id=job_submission.id)

            if response.slurm_job_id is not None:
                return response
            elif response.status in {JobSubmissionStatus.UNKNOWN, JobSubmissionStatus.REJECTED}:
                raise Exception(
                    "Impossible to recover slurm_job_id from job status {}. The report message is: {}".format(
                        response.status, response.report_message
                    )
                )

            time.sleep(waiting_interval)
        raise Exception("Timeout waiting for slurm_job_id")

    def delete(self, id: int) -> None:
        """Delete a job submission by id."""
        response = requests.delete(
            url=f"{self.jobbergate_api_url}/job-submissions/{id}",
            auth=self.jobbergate_auth,
        )
        response.raise_for_status()
