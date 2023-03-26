from dataclasses import dataclass
import time

import requests
from jobbergate_core.apps.job_submissions.constants import JobSubmissionStatus

from jobbergate_core.apps.job_submissions.schemas import JobSubmissionCreateRequest, JobSubmissionResponse
from jobbergate_core.auth.handler import JobbergateAuthHandler


@dataclass
class JobSubmission:
    jobbergate_api_url: str
    jobbergate_auth: JobbergateAuthHandler

    def create(self, create_data: JobSubmissionCreateRequest) -> JobSubmissionResponse:
        response = requests.post(
            url=f"{self.jobbergate_api_url}/job-submissions",
            auth=self.jobbergate_auth,
            json=create_data.dict(exclude_unset=True, exclude_none=True),
        )
        response.raise_for_status()
        return JobSubmissionResponse(**response.json())

    def get(self, id: int) -> JobSubmissionResponse:
        response = requests.get(
            url=f"{self.jobbergate_api_url}/job-submissions/{id}",
            auth=self.jobbergate_auth,
        )
        response.raise_for_status()
        return JobSubmissionResponse(**response.json())

    def get_ensure_slurm_id(
        self,
        id: int,
        time_out: int = 120,
        waiting_interval: int = 30,
    ) -> JobSubmissionResponse:
        expires_at = time.time() + time_out
        while expires_at > time.time():
            response = self.get(id=id)

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
        response = requests.delete(
            url=f"{self.jobbergate_api_url}/job-submissions/{id}",
            auth=self.jobbergate_auth,
        )
        response.raise_for_status()
