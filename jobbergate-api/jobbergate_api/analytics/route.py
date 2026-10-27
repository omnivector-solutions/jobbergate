"""Analytics API endpoints.

These endpoints serve the same aggregations as the Prometheus-format ``/metrics``
endpoints, but as JSON, for consumers that want windowed reports on demand: the
Grafana Infinity datasource, the Jobbergate CLI, and batch exports. The data is
aggregated in the database by time bucket keyed on ``created_at``, so the reports
are exact within the database retention window.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select

from jobbergate_api.analytics.schemas import (
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
from jobbergate_api.metrics.collector import MetricsInterval
from jobbergate_api.metrics.route import MetricsEndTime, MetricsStartTime, resolve_window

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
AnalyticsIntervalQuery = Annotated[
    MetricsInterval,
    Query(description="Time bucket size for aggregation: hour, day, or week."),
]


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
    start_time: MetricsStartTime = None,
    end_time: MetricsEndTime = None,
    interval: AnalyticsIntervalQuery = MetricsInterval.DAY,
) -> TemplateUsageReport:
    start_time, end_time = resolve_window(start_time, end_time)
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
    start_time: MetricsStartTime = None,
    end_time: MetricsEndTime = None,
    interval: AnalyticsIntervalQuery = MetricsInterval.DAY,
) -> SubmissionStatusReport:
    start_time, end_time = resolve_window(start_time, end_time)
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
