"""Metrics API endpoints.

These endpoints expose gauges computed from the database at scrape time, in
Prometheus text exposition format. They are designed to be scraped on a fixed
interval (e.g. by vmagent or Prometheus): once a sample is scraped, its history
lives in the time-series database, independent of the API database retention.

The values cover the rows currently retained in the database, so the retention
purge makes them decrease; they are gauges, not counters, and must be queried
with gauge functions (raw values, ``delta()``), never ``increase()``. Each
endpoint also exposes the configured retention periods as
``jobbergate_retention_days`` so dashboards can see the window.

Because the values are computed from the database rather than held in process
memory, every API replica returns the same answer, so scraping through a load
balancer is safe.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.registry import Collector
from sqlalchemy import func, select

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_scripts.models import JobScript
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.metrics.collector import (
    HealthCollector,
    RetentionCollector,
    SubmissionStatusCollector,
    TemplateSelectionCollector,
)

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A removed time-window parameter was supplied."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication is required."},
        status.HTTP_403_FORBIDDEN: {"description": "The caller lacks metrics read permission."},
    },
)

PROMETHEUS_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "Metrics in Prometheus text exposition format.",
        "content": {CONTENT_TYPE_LATEST: {}},
    },
}

MetricsServices = Annotated[
    SecureService,
    Depends(secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)),
]

_REMOVED_PARAMS = frozenset({"start_time", "end_time", "interval"})


def _reject_removed_params(request: Request) -> None:
    """Fail loudly for legacy clients that still send the removed time-window parameters.

    Called inside the endpoints, after authentication, so unauthenticated requests
    still receive 401 rather than leaking parameter semantics.
    """
    removed = _REMOVED_PARAMS & request.query_params.keys()
    if removed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Query parameters no longer supported: {', '.join(sorted(removed))}. "
                "Metrics are computed over the database retention window at scrape time; "
                "derive time windows at query time in your monitoring stack instead."
            ),
        )


def _response(*collectors: Collector) -> Response:
    registry = CollectorRegistry()
    for collector in collectors:
        registry.register(collector)
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@router.get(
    "/templates",
    summary="Get job template selection metrics",
    description=(
        "Returns the number of retained job submissions for each job template identifier, "
        "grouped by cluster. Templates without an identifier use a template_id:<id> fallback label. "
        "Values cover the database retention window and can decrease; query them as gauges."
    ),
    response_class=Response,
    responses=PROMETHEUS_RESPONSE,
)
async def template_metrics(request: Request, secure_services: MetricsServices):
    _reject_removed_params(request)
    result = await secure_services.session.execute(
        select(
            JobSubmission.client_id,
            JobScriptTemplate.id,
            JobScriptTemplate.identifier,
            func.count(JobSubmission.id),
        )
        .join(JobScript, JobScript.parent_template_id == JobScriptTemplate.id)
        .join(JobSubmission, JobSubmission.job_script_id == JobScript.id)
        .group_by(JobSubmission.client_id, JobScriptTemplate.id, JobScriptTemplate.identifier)
        .order_by(JobSubmission.client_id, JobScriptTemplate.id, JobScriptTemplate.identifier)
    )
    return _response(TemplateSelectionCollector(result.all()), RetentionCollector())


@router.get(
    "/health",
    summary="Get API and agent health metrics",
    description="Returns the current API health and the latest reported health status for each registered agent.",
    response_class=Response,
    responses=PROMETHEUS_RESPONSE,
)
async def health_metrics(request: Request, secure_services: MetricsServices):
    _reject_removed_params(request)
    result = await secure_services.session.execute(select(ClusterStatus).order_by(ClusterStatus.client_id))
    return _response(HealthCollector(result.scalars().all()), RetentionCollector())


@router.get(
    "/submissions",
    summary="Get job submission status metrics",
    description=(
        "Returns counts of retained job submissions by Jobbergate and Slurm status, "
        "grouped by cluster. Each submission is counted under its latest known status. "
        "Values cover the database retention window and can decrease; query them as gauges."
    ),
    response_class=Response,
    responses=PROMETHEUS_RESPONSE,
)
async def submission_metrics(request: Request, secure_services: MetricsServices):
    _reject_removed_params(request)
    result = await secure_services.session.execute(
        select(
            JobSubmission.client_id,
            JobSubmission.status,
            JobSubmission.slurm_job_state,
            func.count(JobSubmission.id),
        )
        .group_by(JobSubmission.client_id, JobSubmission.status, JobSubmission.slurm_job_state)
        .order_by(JobSubmission.client_id, JobSubmission.status, JobSubmission.slurm_job_state)
    )
    return _response(SubmissionStatusCollector(result.all()), RetentionCollector())
