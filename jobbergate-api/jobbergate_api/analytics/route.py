"""Analytics API endpoints.

These endpoints serve time-windowed aggregations as JSON, for consumers that want
reports on demand: the Grafana Infinity datasource, the Jobbergate CLI, and batch
exports. The data is aggregated in the database by time bucket keyed on
``created_at``, so the reports are exact within the database retention window.
They complement the Prometheus-format ``/metrics`` endpoints, which expose the
current retained totals for interval scraping.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from jobbergate_api.analytics.schemas import (
    ReportInterval,
    SubmissionStatusReport,
    SubmissionStatusRow,
    TemplateUsageReport,
    TemplateUsageRow,
)
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.config import settings
from jobbergate_api.utils.time import ensure_utc

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "The requested time range is invalid."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication is required."},
        status.HTTP_403_FORBIDDEN: {"description": "The caller lacks metrics read permission."},
    },
)

AnalyticsServices = Annotated[
    SecureService,
    Depends(secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)),
]
StartTimeQuery = Annotated[
    datetime | None,
    Query(
        description=(
            "Inclusive start of the UTC reporting window. Submissions are selected by created_at. "
            "Values without a timezone offset are assumed to be UTC. "
            "Defaults to one day before end_time."
        )
    ),
]
EndTimeQuery = Annotated[
    datetime | None,
    Query(
        description=(
            "Inclusive end of the UTC reporting window, based on submission created_at. "
            "Values without a timezone offset are assumed to be UTC. "
            "Defaults to the current time. For finalized reports, set this earlier than now "
            "to allow recent submissions to reach a final status."
        )
    ),
]
IntervalQuery = Annotated[
    ReportInterval,
    Query(description="Time bucket size for aggregation: hour, day, or week."),
]

_INTERVAL_WIDTH = {
    ReportInterval.HOUR: timedelta(hours=1),
    ReportInterval.DAY: timedelta(days=1),
    ReportInterval.WEEK: timedelta(weeks=1),
}
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
# date_trunc('week') truncates to Monday, but the epoch is a Thursday, so week
# boundaries sit 3 days before epoch-aligned multiples.
_WEEK_ALIGNMENT = timedelta(days=3)


def _bucket_count(start_time: datetime, end_time: datetime, interval: ReportInterval) -> int:
    """Count the distinct date_trunc buckets the window spans, bucket-boundary aligned."""
    width = _INTERVAL_WIDTH[interval]
    offset = _WEEK_ALIGNMENT if interval is ReportInterval.WEEK else timedelta(0)
    return (end_time - _EPOCH + offset) // width - (start_time - _EPOCH + offset) // width + 1


def resolve_window(
    start_time: datetime | None, end_time: datetime | None, interval: ReportInterval
) -> tuple[datetime, datetime]:
    """Apply the window defaults and reject inverted or oversized ranges."""
    end_time = ensure_utc(end_time) or datetime.now(timezone.utc)
    start_time = ensure_utc(start_time) or end_time - timedelta(days=1)
    if end_time < start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be greater than the start time."
        )
    buckets = _bucket_count(start_time, end_time, interval)
    if buckets > settings.ANALYTICS_MAX_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The requested window spans {buckets} {interval.value} buckets, "
                f"exceeding the maximum of {settings.ANALYTICS_MAX_BUCKETS}. "
                "Use a coarser interval or a shorter time window."
            ),
        )
    return start_time, end_time


@router.get(
    "/templates",
    summary="Get job template usage report",
    description=(
        "Returns the number of job submissions for each job template identifier, "
        "grouped by cluster and into hourly, daily, or weekly time buckets, as JSON. "
        "Templates without an identifier use a template_id:<id> fallback. "
        "Submissions are selected by created_at, so the report is exact within the "
        "database retention window."
    ),
)
async def template_usage_report(
    secure_services: AnalyticsServices,
    start_time: StartTimeQuery = None,
    end_time: EndTimeQuery = None,
    interval: IntervalQuery = ReportInterval.DAY,
) -> TemplateUsageReport:
    start_time, end_time = resolve_window(start_time, end_time, interval)
    result = await secure_services.session.execute(
        select(
            func.date_trunc(interval.value, JobSubmission.created_at).label("bucket"),
            JobSubmission.client_id,
            JobScriptTemplate.id,
            JobScriptTemplate.identifier,
            func.count(JobSubmission.id),
        )
        .join(JobScript, JobScript.parent_template_id == JobScriptTemplate.id)
        .join(JobSubmission, JobSubmission.job_script_id == JobScript.id)
        .where(JobSubmission.created_at >= start_time, JobSubmission.created_at <= end_time)
        .group_by("bucket", JobSubmission.client_id, JobScriptTemplate.id, JobScriptTemplate.identifier)
        .order_by("bucket", JobSubmission.client_id, JobScriptTemplate.id, JobScriptTemplate.identifier)
    )
    return TemplateUsageReport(
        start_time=start_time,
        end_time=end_time,
        interval=interval,
        items=[
            TemplateUsageRow(
                bucket=bucket,
                client_id=client_id,
                template_id=template_id,
                template_identifier=identifier or f"template_id:{template_id}",
                count=count,
            )
            for bucket, client_id, template_id, identifier, count in result.all()
        ],
    )


@router.get(
    "/submissions",
    summary="Get job submission status report",
    description=(
        "Returns counts of Jobbergate and Slurm submission statuses, grouped by cluster "
        "and into hourly, daily, or weekly time buckets, as JSON. Submissions are "
        "selected by created_at and their latest known status is reported, so the "
        "report is exact within the database retention window."
    ),
)
async def submission_status_report(
    secure_services: AnalyticsServices,
    start_time: StartTimeQuery = None,
    end_time: EndTimeQuery = None,
    interval: IntervalQuery = ReportInterval.DAY,
) -> SubmissionStatusReport:
    start_time, end_time = resolve_window(start_time, end_time, interval)
    result = await secure_services.session.execute(
        select(
            func.date_trunc(interval.value, JobSubmission.created_at).label("bucket"),
            JobSubmission.client_id,
            JobSubmission.status,
            JobSubmission.slurm_job_state,
            func.count(JobSubmission.id),
        )
        .where(JobSubmission.created_at >= start_time, JobSubmission.created_at <= end_time)
        .group_by("bucket", JobSubmission.client_id, JobSubmission.status, JobSubmission.slurm_job_state)
        .order_by("bucket", JobSubmission.client_id, JobSubmission.status, JobSubmission.slurm_job_state)
    )
    return SubmissionStatusReport(
        start_time=start_time,
        end_time=end_time,
        interval=interval,
        items=[
            SubmissionStatusRow(
                bucket=bucket,
                client_id=client_id,
                status=submission_status.value,
                slurm_job_state=slurm_job_state.value if slurm_job_state is not None else None,
                count=count,
            )
            for bucket, client_id, submission_status, slurm_job_state, count in result.all()
        ],
    )
