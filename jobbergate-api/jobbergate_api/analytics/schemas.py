"""Schemas for the analytics reporting endpoints."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ReportInterval(StrEnum):
    """Supported time buckets for report aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class TemplateUsageRow(BaseModel):
    """Job submission count for one template, cluster, and time bucket.

    ``template_id`` is the stable key for the template; ``template_identifier`` is a
    display name that can be assigned or changed after the fact. Submissions whose
    job script or template was deleted (or that never had one) carry a null
    ``template_id`` and the identifier ``unknown``.
    """

    bucket: datetime
    client_id: str
    template_id: int | None
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
    interval: ReportInterval
    items: list[TemplateUsageRow]


class SubmissionStatusReport(BaseModel):
    """Submission status rows along with the resolved reporting window."""

    start_time: datetime
    end_time: datetime
    interval: ReportInterval
    items: list[SubmissionStatusRow]
