"""Prometheus collectors for Jobbergate metrics.

All families are gauges: the values are computed from the database at scrape
time, and the retention purge removes old rows, so the counts cover the
database retention window and can decrease. They must not be exposed as
counters, or PromQL's ``increase()``/``rate()`` would misread every decrease as
a counter reset.
"""

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.config import settings

RETENTION_SETTINGS: dict[tuple[str, str], Callable[[], int | None]] = {
    ("job_script_templates", "archive"): lambda: settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_ARCHIVE,
    ("job_script_templates", "delete"): lambda: settings.AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_DELETE,
    ("job_scripts", "archive"): lambda: settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE,
    ("job_scripts", "delete"): lambda: settings.AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE,
    ("job_submissions", "archive"): lambda: settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE,
    ("job_submissions", "delete"): lambda: settings.AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE,
}


class RetentionCollector(Collector):
    """Expose the configured auto-clean periods that bound the retention window."""

    def collect(self) -> Iterable[GaugeMetricFamily]:
        metric = GaugeMetricFamily(
            "jobbergate_retention_days",
            "Configured auto-clean period in days per resource and action. "
            "Deletions bound the window the other metric families can cover; absent when not configured.",
            labels=["resource", "action"],
        )
        for (resource, action), get_days in RETENTION_SETTINGS.items():
            days = get_days()
            if days is not None:
                metric.add_metric([resource, action], days)
        yield metric


class HealthCollector(Collector):
    """Expose the API health and the current health of each registered agent."""

    def __init__(self, cluster_statuses: Sequence[ClusterStatus]):
        self.cluster_statuses = cluster_statuses

    def collect(self) -> Iterable[GaugeMetricFamily]:
        metric = GaugeMetricFamily("jobbergate_api_health_status", "Health status of the Jobbergate API.")
        metric.add_metric([], 1)
        yield metric
        metric = GaugeMetricFamily(
            "jobbergate_agent_health_status",
            "Current health status of registered Jobbergate agents.",
            labels=["client_id"],
        )
        for cluster_status in self.cluster_statuses:
            metric.add_metric([cluster_status.client_id], int(cluster_status.is_healthy))
        yield metric


class RowValuesCollector(Collector):
    """Hold the database rows a collector formats into a metric family."""

    def __init__(self, values: Sequence[Any]):
        self.values = values


class TemplateSelectionCollector(RowValuesCollector):
    """Expose the number of retained job submissions grouped by job template."""

    def collect(self) -> Iterable[GaugeMetricFamily]:
        metric = GaugeMetricFamily(
            "jobbergate_job_submissions_by_template",
            "Job submissions retained in the database, grouped by job template identifier. "
            "Limited to the database retention window.",
            labels=["client_id", "template_identifier"],
        )
        for client_id, template_id, identifier, count in self.values:
            template_identifier = identifier or f"template_id:{template_id}"
            metric.add_metric([client_id, template_identifier], count)
        yield metric


class SubmissionStatusCollector(RowValuesCollector):
    """Expose the number of retained job submissions grouped by their latest status."""

    def collect(self) -> Iterable[GaugeMetricFamily]:
        metric = GaugeMetricFamily(
            "jobbergate_job_submissions_by_status",
            "Job submissions retained in the database, grouped by their latest Jobbergate and Slurm status. "
            "Limited to the database retention window.",
            labels=["client_id", "status", "slurm_job_state"],
        )
        for client_id, submission_status, slurm_job_state, count in self.values:
            metric.add_metric(
                [
                    client_id,
                    submission_status.value,
                    slurm_job_state.value if slurm_job_state is not None else "unknown",
                ],
                count,
            )
        yield metric
