"""Prometheus collectors for Jobbergate metrics."""

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector


class MetricsInterval(StrEnum):
    """Supported time buckets for metrics aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class MetricsCollector(Collector):
    """Format one Jobbergate metric family for Prometheus."""

    def __init__(self, metric_name, values):
        self.metric_name = metric_name
        self.values = values

    def collect(self):
        if self.metric_name == "health":
            metric = GaugeMetricFamily("jobbergate_api_health_status", "Health status of the Jobbergate API.")
            metric.add_metric([], 1)
            yield metric
            metric = GaugeMetricFamily(
                "jobbergate_agent_health_status",
                "Current health status of registered Jobbergate agents.",
                labels=["client_id"],
            )
            now = datetime.now(timezone.utc)
            for client_id, last_reported, interval in self.values:
                metric.add_metric([client_id], int(last_reported >= now - timedelta(seconds=interval)))
            yield metric
        elif self.metric_name == "templates":
            metric = GaugeMetricFamily(
                "jobbergate_job_template_selection_total",
                "Job submissions grouped by job template identifier.",
                labels=["bucket", "client_id", "template_identifier"],
            )
            for bucket, client_id, template_id, identifier, count in self.values:
                template_identifier = identifier or f"template_id:{template_id}"
                metric.add_metric([bucket.isoformat(), client_id, template_identifier], count)
            yield metric
        else:
            metric = GaugeMetricFamily(
                "jobbergate_job_submission_status_total",
                "Job submissions grouped by Jobbergate and Slurm status.",
                labels=["bucket", "client_id", "status", "slurm_job_state"],
            )
            for bucket, client_id, submission_status, slurm_job_state, count in self.values:
                metric.add_metric(
                    [
                        bucket.isoformat(),
                        client_id,
                        submission_status.value,
                        slurm_job_state.value if slurm_job_state is not None else "unknown",
                    ],
                    count,
                )
            yield metric
