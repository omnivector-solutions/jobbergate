from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from prometheus_client import CollectorRegistry, generate_latest

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.metrics import MetricsCollector


def test_metrics_collector_exposes_usage_and_status_metrics():
    now = datetime.now(timezone.utc)
    registry = CollectorRegistry()
    registry.register(
        MetricsCollector(
            "templates",
            [(now, "template-a", 3)],
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_job_template_selection_total{bucket="' in body
    assert 'template_identifier="template-a"} 3.0' in body


def test_metrics_collector_marks_stale_agents_unhealthy():
    now = datetime.now(timezone.utc)
    registry = CollectorRegistry()
    registry.register(
        MetricsCollector(
            "health",
            [("cluster-a", now - timedelta(seconds=61), 60)],
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_agent_health_status{client_id="cluster-a"} 0.0' in body


def test_metrics_collector_exposes_submission_status_metrics():
    now = datetime.now(timezone.utc)
    registry = CollectorRegistry()
    registry.register(
        MetricsCollector(
            "submissions",
            [(now, JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING, 2)],
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_job_submission_status_total{bucket="' in body
    assert 'slurm_job_state="RUNNING",status="SUBMITTED"} 2.0' in body


@pytest.mark.parametrize("path", ("templates", "health", "submissions"))
async def test_metrics_routes_require_authentication(client: AsyncClient, path: str):
    response = await client.get(f"/jobbergate/metrics/{path}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("path", ("templates", "health", "submissions"))
async def test_metrics_routes_require_metrics_permission(
    client: AsyncClient, inject_security_header, tester_email: str, path: str
):
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_READ)

    response = await client.get(f"/jobbergate/metrics/{path}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_metrics_routes_reject_invalid_time_range(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/metrics/{path}",
        params={"start_time": "2026-09-08T12:00:00Z", "end_time": "2026-09-08T11:00:00Z"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "End time must be greater than the start time."


async def test_metrics_routes_reject_unknown_interval(
    client: AsyncClient, inject_security_header, tester_email: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get("/jobbergate/metrics/submissions", params={"interval": "month"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_health_metrics_returns_prometheus_content(
    client: AsyncClient, inject_security_header, tester_email: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get("/jobbergate/metrics/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/plain")
    assert "jobbergate_api_health_status 1.0" in response.text
