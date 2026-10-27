"""Schemas for the analytics reporting endpoints."""

from datetime import datetime

from pydantic import BaseModel

from jobbergate_api.metrics.collector import MetricsInterval


class TemplateUsageRow(BaseModel):
    """Job submission count for one template, cluster, and time bucket."""

    bucket: datetime
    client_id: str
    template_identifier: str
    count: int


class SubmissionStatusRow(BaseModel):
    """Job submission count for one status combination, cluster, and time bucket."""

    bucket: datetime
    client_id: str
    status: str
    slurm_job_state: str | None
    count: int


class TemplateUsageReport(BaseModel):
    """Template usage rows along with the resolved reporting window."""

    start_time: datetime
    end_time: datetime
    interval: MetricsInterval
    items: list[TemplateUsageRow]


class SubmissionStatusReport(BaseModel):
    """Submission status rows along with the resolved reporting window."""

    start_time: datetime
    end_time: datetime
    interval: MetricsInterval
    items: list[SubmissionStatusRow]
