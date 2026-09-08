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
            [
                (now, "cluster-a", 1, "template-a", 3),
                (now, "cluster-b", 1, "template-a", 2),
                (now, "cluster-a", 2, None, 1),
                (now, "cluster-a", 3, None, 1),
            ],
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_job_template_selection_total{bucket="' in body
    assert 'client_id="cluster-a",template_identifier="template-a"} 3.0' in body
    assert 'client_id="cluster-b",template_identifier="template-a"} 2.0' in body
    assert 'client_id="cluster-a",template_identifier="template_id:2"} 1.0' in body
    assert 'client_id="cluster-a",template_identifier="template_id:3"} 1.0' in body


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
            [(now, "cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING, 2)],
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_job_submission_status_total{bucket="' in body
    assert 'client_id="cluster-a",slurm_job_state="RUNNING",status="SUBMITTED"} 2.0' in body


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


async def test_template_metrics_aggregate_by_client_and_interval(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    template = await synth_services.crud.template.create(
        name="metrics-template",
        description="Metrics template",
        owner_email=tester_email,
        is_archived=False,
        identifier="template-a",
    )
    script_a = await synth_services.crud.job_script.create(
        name="metrics-script-a",
        description="Metrics script A",
        owner_email=tester_email,
        is_archived=False,
        parent_template_id=template.id,
    )
    script_b = await synth_services.crud.job_script.create(
        name="metrics-script-b",
        description="Metrics script B",
        owner_email=tester_email,
        is_archived=False,
        parent_template_id=template.id,
    )
    start_time = datetime(2026, 9, 8, 11, tzinfo=timezone.utc)
    end_time = datetime(2026, 9, 8, 14, tzinfo=timezone.utc)
    await synth_services.crud.job_submission.create(
        name="metrics-submission-a",
        description="Metrics submission A",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        job_script_id=script_a.id,
        client_id="cluster-a",
        created_at=datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc),
    )
    await synth_services.crud.job_submission.create(
        name="metrics-submission-b",
        description="Metrics submission B",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        job_script_id=script_b.id,
        client_id="cluster-b",
        created_at=datetime(2026, 9, 8, 12, 45, tzinfo=timezone.utc),
    )
    await synth_services.crud.job_submission.create(
        name="metrics-submission-outside-window",
        description="Outside metrics window",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        job_script_id=script_a.id,
        client_id="cluster-a",
        created_at=datetime(2026, 9, 8, 15, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/jobbergate/metrics/templates",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "hour",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'client_id="cluster-a",template_identifier="template-a"} 1.0' in response.text
    assert 'client_id="cluster-b",template_identifier="template-a"} 1.0' in response.text
    assert 'client_id="cluster-a",template_identifier="template-a"} 2.0' not in response.text


async def test_submission_metrics_aggregate_by_client_and_status_in_time_window(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    start_time = datetime(2026, 9, 8, 11, tzinfo=timezone.utc)
    end_time = datetime(2026, 9, 8, 14, tzinfo=timezone.utc)
    await synth_services.crud.job_submission.create(
        name="metrics-submission-running",
        description="Running metrics submission",
        owner_email=tester_email,
        is_archived=False,
        sbatch_arguments=[],
        client_id="cluster-a",
        status=JobSubmissionStatus.SUBMITTED,
        slurm_job_state=SlurmJobState.RUNNING,
        created_at=datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc),
    )
    await synth_services.crud.job_submission.create(
        name="metrics-submission-completed",
        description="Completed metrics submission",
        owner_email=tester_email,
        is_archived=False,
        sbatch_arguments=[],
        client_id="cluster-b",
        status=JobSubmissionStatus.DONE,
        slurm_job_state=SlurmJobState.COMPLETED,
        created_at=datetime(2026, 9, 8, 12, 45, tzinfo=timezone.utc),
    )
    await synth_services.crud.job_submission.create(
        name="metrics-submission-outside-window",
        description="Outside metrics window",
        owner_email=tester_email,
        is_archived=False,
        sbatch_arguments=[],
        client_id="cluster-a",
        status=JobSubmissionStatus.SUBMITTED,
        slurm_job_state=SlurmJobState.RUNNING,
        created_at=datetime(2026, 9, 8, 15, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/jobbergate/metrics/submissions",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "hour",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'client_id="cluster-a",slurm_job_state="RUNNING",status="SUBMITTED"} 1.0' in response.text
    assert 'client_id="cluster-b",slurm_job_state="COMPLETED",status="DONE"} 1.0' in response.text
    assert 'client_id="cluster-a",slurm_job_state="RUNNING",status="SUBMITTED"} 2.0' not in response.text


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_metrics_aggregation_returns_empty_families_for_empty_window(
    client: AsyncClient, inject_security_header, tester_email: str, synth_session, path: str
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/metrics/{path}",
        params={
            "start_time": "2026-09-08T11:00:00Z",
            "end_time": "2026-09-08T12:00:00Z",
            "interval": "day",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert "# TYPE" in response.text
    assert 'client_id="' not in response.text
