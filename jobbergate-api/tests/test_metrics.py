from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from prometheus_client import CollectorRegistry, generate_latest

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.metrics import (
    HealthCollector,
    RetentionCollector,
    SubmissionStatusCollector,
    TemplateSelectionCollector,
)


def test_template_selection_collector_exposes_gauges_by_template():
    registry = CollectorRegistry()
    registry.register(
        TemplateSelectionCollector(
            [
                ("cluster-a", 1, "template-a", 3),
                ("cluster-b", 1, "template-a", 2),
                ("cluster-a", 2, None, 1),
                ("cluster-a", 3, None, 1),
            ]
        )
    )

    body = generate_latest(registry).decode()

    assert "# TYPE jobbergate_job_submissions_by_template gauge" in body
    assert 'jobbergate_job_submissions_by_template{client_id="cluster-a",template_identifier="template-a"} 3.0' in body
    assert 'jobbergate_job_submissions_by_template{client_id="cluster-b",template_identifier="template-a"} 2.0' in body
    assert 'client_id="cluster-a",template_identifier="template_id:2"} 1.0' in body
    assert 'client_id="cluster-a",template_identifier="template_id:3"} 1.0' in body


def test_health_collector_marks_stale_agents_unhealthy():
    now = datetime.now(timezone.utc)
    registry = CollectorRegistry()
    registry.register(
        HealthCollector(
            [
                ClusterStatus(client_id="cluster-a", interval=60, last_reported=now - timedelta(seconds=61)),
                ClusterStatus(client_id="cluster-b", interval=60, last_reported=now),
            ]
        )
    )

    body = generate_latest(registry).decode()

    assert 'jobbergate_agent_health_status{client_id="cluster-a"} 0.0' in body
    assert 'jobbergate_agent_health_status{client_id="cluster-b"} 1.0' in body


def test_retention_collector_exposes_configured_retention(tweak_settings):
    registry = CollectorRegistry()
    registry.register(RetentionCollector())

    with tweak_settings(
        AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE=90,
        AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE=30,
    ):
        body = generate_latest(registry).decode()

    assert 'jobbergate_retention_days{action="delete",resource="job_submissions"} 90.0' in body
    assert 'jobbergate_retention_days{action="archive",resource="job_submissions"} 30.0' in body
    assert 'resource="job_scripts"' not in body


def test_submission_status_collector_exposes_gauges_by_status():
    registry = CollectorRegistry()
    registry.register(
        SubmissionStatusCollector([("cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING, 2)])
    )

    body = generate_latest(registry).decode()

    assert "# TYPE jobbergate_job_submissions_by_status gauge" in body
    assert (
        "jobbergate_job_submissions_by_status"
        '{client_id="cluster-a",slurm_job_state="RUNNING",status="SUBMITTED"} 2.0' in body
    )


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


@pytest.mark.parametrize("param", ("start_time", "end_time", "interval"))
@pytest.mark.parametrize("path", ("templates", "health", "submissions"))
async def test_metrics_routes_reject_removed_time_window_params(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, param: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(f"/jobbergate/metrics/{path}", params={param: "2026-09-08T12:00:00Z"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert param in response.json()["detail"]


@pytest.mark.parametrize("path", ("templates", "health", "submissions"))
async def test_metrics_routes_check_authentication_before_removed_params(client: AsyncClient, path: str):
    response = await client.get(f"/jobbergate/metrics/{path}", params={"start_time": "2026-09-08T12:00:00Z"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_health_metrics_returns_prometheus_content(
    client: AsyncClient, inject_security_header, tester_email: str, synth_session, tweak_settings
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    with tweak_settings(AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE=90):
        response = await client.get("/jobbergate/metrics/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/plain")
    assert "jobbergate_api_health_status 1.0" in response.text
    assert 'jobbergate_retention_days{action="delete",resource="job_submissions"} 90.0' in response.text


async def test_template_metrics_report_retained_totals_by_client(
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
    for name, script_id, client_id, created_at in (
        ("metrics-submission-a", script_a.id, "cluster-a", datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc)),
        ("metrics-submission-b", script_b.id, "cluster-b", datetime(2026, 9, 8, 12, 45, tzinfo=timezone.utc)),
        ("metrics-submission-c", script_a.id, "cluster-a", datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)),
    ):
        await synth_services.crud.job_submission.create(
            name=name,
            description="Metrics submission",
            owner_email=tester_email,
            is_archived=False,
            status=JobSubmissionStatus.CREATED,
            sbatch_arguments=[],
            job_script_id=script_id,
            client_id=client_id,
            created_at=created_at,
        )

    response = await client.get("/jobbergate/metrics/templates")

    assert response.status_code == status.HTTP_200_OK
    assert (
        'jobbergate_job_submissions_by_template{client_id="cluster-a",template_identifier="template-a"} 2.0'
        in response.text
    )
    assert (
        'jobbergate_job_submissions_by_template{client_id="cluster-b",template_identifier="template-a"} 1.0'
        in response.text
    )


async def test_submission_metrics_report_retained_totals_by_client_and_status(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    for name, client_id, submission_status, slurm_job_state in (
        ("metrics-submission-running-1", "cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING),
        ("metrics-submission-running-2", "cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING),
        ("metrics-submission-completed", "cluster-b", JobSubmissionStatus.DONE, SlurmJobState.COMPLETED),
    ):
        await synth_services.crud.job_submission.create(
            name=name,
            description="Metrics submission",
            owner_email=tester_email,
            is_archived=False,
            sbatch_arguments=[],
            client_id=client_id,
            status=submission_status,
            slurm_job_state=slurm_job_state,
        )

    response = await client.get("/jobbergate/metrics/submissions")

    assert response.status_code == status.HTTP_200_OK
    assert (
        "jobbergate_job_submissions_by_status"
        '{client_id="cluster-a",slurm_job_state="RUNNING",status="SUBMITTED"} 2.0' in response.text
    )
    assert (
        "jobbergate_job_submissions_by_status"
        '{client_id="cluster-b",slurm_job_state="COMPLETED",status="DONE"} 1.0' in response.text
    )


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_metrics_return_empty_families_without_data(
    client: AsyncClient, inject_security_header, tester_email: str, synth_session, path: str
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(f"/jobbergate/metrics/{path}")

    assert response.status_code == status.HTTP_200_OK
    assert "# TYPE" in response.text
    assert "# TYPE jobbergate_retention_days gauge" in response.text
    assert 'client_id="' not in response.text
