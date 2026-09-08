from datetime import datetime, timedelta, timezone

from prometheus_client import CollectorRegistry, generate_latest

from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
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
