"""Core helper functions for job submissions."""

from collections.abc import Iterable
from math import ceil
from textwrap import dedent
from typing import Any, assert_never, Type

from loguru import logger

from jobbergate_api.apps.job_submissions.constants import (
    JobSubmissionMetricSampleRate,
    JobSubmissionMetricAggregateNames,
)


def validate_job_metric_upload_input(
    data: Any, expected_types: tuple[Type[Any], ...]
) -> Iterable[tuple[Any, ...]]:
    """Validate if the input data of job metric upload is correct once decoded.

    It will brute force apply the expected types to the data and raise an error in case it fails.

    Args:
        data (Iterable[list[Any] | tuple[Any]]): The decoded data, which should be a list of lists or tuples,
            where each inner list or tuple contains the data for a single job metric upload.
        expected_types (tuple[Type[Any], ...]): A tuple of types that each element in the inner lists or tuples
            should match.

    Returns:
        Iterable[tuple[Any, ...]]: The validated data, where each tuple has the same length as expected_types.
    """

    def _force_cast(object: Any, expected_type: Type[Any]) -> Any:
        try:
            return expected_type(object)
        except Exception as e:
            logger.error(f"Failed to cast data to expected types: {e}")
            raise ValueError("Failed to cast data to expected types") from e

    if not isinstance(data, list):
        raise ValueError("Decoded data must be a list.")
    if not all(isinstance(x, (list, tuple)) for x in data):
        raise ValueError("All elements of the inner data must be a Sequence")
    if not all(len(x) == len(expected_types) for x in data):
        raise ValueError("Every iterable in `data` must match the length of `expected_types`.")
    # postgres limits the number of query params to 2**15 - 1
    # https://www.postgresql.org/docs/17/protocol-message-formats.html
    if len(expected_types) * len(data) > 2**15 - 1:
        raise ValueError(
            "The maximum number of elements has been exceeded. Maximum is {}, received {}".format(
                ceil((2**15 - 1) / len(expected_types)), len(data)
            )
        )

    return (
        tuple(_force_cast(data, expected_types[idx]) for idx, data in enumerate(aggregated_data))
        for aggregated_data in data
    )


def build_job_metric_aggregation_query(node: str | None, sample_rate: JobSubmissionMetricSampleRate) -> str:
    """
    Build a SQL query string to aggregate job metrics based on the provided node and sample rate.

    Args:
        node (str | None): The node host identifier. If None, the query will aggregate metrics for all nodes.
        sample_rate (JobSubmissionMetricSampleRate): The sample rate for the metrics aggregation. Determines the view name to use.

    Returns:
        str: The SQL query string for aggregating job metrics.
    """
    if node is not None:
        where_statement = "WHERE job_submission_id = :job_submission_id AND node_host = :node_host"
        match sample_rate:
            case JobSubmissionMetricSampleRate.ten_seconds:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_seconds_by_node
            case JobSubmissionMetricSampleRate.one_minute:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_minute_by_node
            case JobSubmissionMetricSampleRate.ten_minutes:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_minutes_by_node
            case JobSubmissionMetricSampleRate.one_hour:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_hour_by_node
            case JobSubmissionMetricSampleRate.one_week:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_week_by_node
            case _ as unreachable:
                assert_never(unreachable)
    else:
        where_statement = "WHERE job_submission_id = :job_submission_id"
        match sample_rate:
            case JobSubmissionMetricSampleRate.ten_seconds:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_seconds_all_nodes
            case JobSubmissionMetricSampleRate.one_minute:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_minute_all_nodes
            case JobSubmissionMetricSampleRate.ten_minutes:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_10_minutes_all_nodes
            case JobSubmissionMetricSampleRate.one_hour:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_hour_all_nodes
            case JobSubmissionMetricSampleRate.one_week:
                view_name = JobSubmissionMetricAggregateNames.metrics_nodes_mv_1_week_all_nodes
            case _ as unreachable:
                assert_never(unreachable)

    return dedent(
        f"""
        SELECT bucket,
            node_host,
            cpu_frequency,
            cpu_time,
            cpu_utilization,
            gpu_memory,
            gpu_utilization,
            page_faults,
            memory_rss,
            memory_virtual,
            disk_read,
            disk_write
        FROM {view_name}
        {where_statement}
        AND bucket >= :start_time
        AND bucket <= :end_time
        ORDER BY bucket
        """
    )
