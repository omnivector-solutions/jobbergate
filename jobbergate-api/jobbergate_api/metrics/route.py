"""Metrics API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from sqlalchemy import func, select

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.metrics.collector import MetricsCollector, MetricsInterval

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication is required."},
        status.HTTP_403_FORBIDDEN: {"description": "The caller lacks metrics read permission."},
    },
)

PROMETHEUS_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "Metrics in Prometheus text exposition format.",
        "content": {CONTENT_TYPE_LATEST: {}},
    },
    status.HTTP_400_BAD_REQUEST: {"description": "The requested time range is invalid."},
}


def _window(start_time: datetime | None, end_time: datetime | None) -> tuple[datetime, datetime]:
    end_time = end_time or datetime.now(timezone.utc)
    start_time = start_time or end_time - timedelta(hours=1)
    if end_time < start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be greater than the start time.")
    return start_time, end_time


def _response(metric_name: str, values) -> Response:
    registry = CollectorRegistry()
    registry.register(MetricsCollector(metric_name, values))
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@router.get(
    "/templates",
    summary="Get job template selection metrics",
    description=(
        "Returns the number of job submissions for each job template identifier, "
        "grouped into hourly, daily, or weekly time buckets."
    ),
    response_class=Response,
    responses=PROMETHEUS_RESPONSE,
)
async def template_metrics(
    secure_services: Annotated[
        SecureService,
        Depends(secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)),
    ],
    start_time: Annotated[
        datetime | None,
        Query(description="Inclusive start of the UTC reporting window. Defaults to one hour before end_time."),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Inclusive end of the UTC reporting window. Defaults to the current time."),
    ] = None,
    interval: Annotated[
        MetricsInterval,
        Query(description="Time bucket size for aggregation: hour, day, or week."),
    ] = MetricsInterval.HOUR,
):
    start_time, end_time = _window(start_time, end_time)
    result = await secure_services.session.execute(
        select(
            func.date_trunc(interval.value, JobSubmission.created_at).label("bucket"),
            JobScriptTemplate.identifier,
            func.count(JobSubmission.id),
        )
        .join(JobScript, JobScript.parent_template_id == JobScriptTemplate.id)
        .join(JobSubmission, JobSubmission.job_script_id == JobScript.id)
        .where(JobSubmission.created_at >= start_time, JobSubmission.created_at <= end_time)
        .group_by("bucket", JobScriptTemplate.identifier)
        .order_by("bucket", JobScriptTemplate.identifier)
    )
    return _response("templates", result.all())


@router.get(
    "/health",
    summary="Get API and agent health metrics",
    description="Returns the current API health and the latest reported health status for each registered agent.",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "description": "Health metrics in Prometheus text exposition format.",
            "content": {CONTENT_TYPE_LATEST: {}},
        },
    },
)
async def health_metrics(
    secure_services: Annotated[
        SecureService,
        Depends(secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)),
    ],
):
    result = await secure_services.session.execute(
        select(ClusterStatus.client_id, ClusterStatus.last_reported, ClusterStatus.interval).order_by(ClusterStatus.client_id)
    )
    return _response("health", result.all())


@router.get(
    "/submissions",
    summary="Get job submission status metrics",
    description=(
        "Returns counts of Jobbergate and Slurm submission statuses, "
        "grouped into hourly, daily, or weekly time buckets."
    ),
    response_class=Response,
    responses=PROMETHEUS_RESPONSE,
)
async def submission_metrics(
    secure_services: Annotated[
        SecureService,
        Depends(secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)),
    ],
    start_time: Annotated[
        datetime | None,
        Query(description="Inclusive start of the UTC reporting window. Defaults to one hour before end_time."),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Inclusive end of the UTC reporting window. Defaults to the current time."),
    ] = None,
    interval: Annotated[
        MetricsInterval,
        Query(description="Time bucket size for aggregation: hour, day, or week."),
    ] = MetricsInterval.HOUR,
):
    start_time, end_time = _window(start_time, end_time)
    result = await secure_services.session.execute(
        select(
            func.date_trunc(interval.value, JobSubmission.created_at).label("bucket"),
            JobSubmission.status,
            JobSubmission.slurm_job_state,
            func.count(JobSubmission.id),
        )
        .where(JobSubmission.created_at >= start_time, JobSubmission.created_at <= end_time)
        .group_by("bucket", JobSubmission.status, JobSubmission.slurm_job_state)
        .order_by("bucket", JobSubmission.status, JobSubmission.slurm_job_state)
    )
    return _response("submissions", result.all())