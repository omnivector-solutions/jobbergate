"""Core module for compute related functions."""

import tracemalloc
from collections.abc import Callable
from functools import wraps
from typing import Any, get_args, cast
from collections.abc import Iterator

import numpy as np
from loguru import logger
from numba import njit

from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT
from jobbergate_agent.jobbergate.schemas import InfluxDBPointDict, JobMetricData


def measure_memory_usage(func: Callable) -> Callable:
    """Decorator to measure the memory usage of a function.

    Args:
        func: Function whose memory usage should be measured.

    Returns:
        Decorated function.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        logger.debug(f"Memory usage for function '{func.__name__}': {current=}B, {peak=}B")
        return result

    return wrapper


def _create_mapping(column):
    """Create a mapping of unique strings to integers."""
    unique_values = sorted(set(column))
    return {val: idx for idx, val in enumerate(unique_values)}


@njit
def _aggregate_with_numba(
    values: np.ndarray, key_indices: np.ndarray, measurement_indices: np.ndarray, num_keys: int, num_measurements: int
):
    """
    Perform aggregation using numba.
    """
    aggregated_values = np.zeros((num_keys, num_measurements), dtype=np.float64)

    for i in range(len(values)):
        key_idx = key_indices[i]
        measurement_idx = measurement_indices[i]
        aggregated_values[key_idx, measurement_idx] += values[i]

    return aggregated_values


@measure_memory_usage
def aggregate_influx_measures(
    data_points: Iterator[InfluxDBPointDict],
) -> JobMetricData:
    """Aggregate the list of data points by time, host, step and task.

    The output data is a list of tuples with the following format:
    [
        (time, host, step, task, CPUFrequency, CPUTime, CPUUtilization, GPUMemMB,
        GPUUtilization, Pages, RSS, VMSize, ReadMB, WriteMB),
        ...
    ]
    """
    measurement_names = get_args(INFLUXDB_MEASUREMENT)
    measurement_mapping = {name: idx for idx, name in enumerate(measurement_names)}
    num_measurements = len(measurement_names)

    data_points_list = list(data_points)

    # Extract columns and map strings to integers
    times = np.fromiter(map(lambda d: d["time"], data_points_list), dtype=np.int64)
    hosts = np.fromiter(map(lambda d: d["host"], data_points_list), dtype=np.object_)
    steps = np.fromiter(map(lambda d: d["step"], data_points_list), dtype=np.object_)
    tasks = np.fromiter(map(lambda d: d["task"], data_points_list), dtype=np.object_)
    measurements = np.fromiter(map(lambda d: measurement_mapping[d["measurement"]], data_points_list), dtype=np.int8)
    values = np.fromiter(map(lambda d: d["value"], data_points_list), dtype=np.float64)

    # Create mappings for string columns
    host_mapping = _create_mapping(hosts)
    step_mapping = _create_mapping(steps)
    task_mapping = _create_mapping(tasks)

    # Map strings to integers
    host_indices = np.array([host_mapping[h] for h in hosts], dtype=np.int64)
    step_indices = np.array([step_mapping[s] for s in steps], dtype=np.int64)
    task_indices = np.array([task_mapping[t] for t in tasks], dtype=np.int64)

    # Combine keys for grouping
    keys = np.stack((times, host_indices, step_indices, task_indices), axis=1)
    unique_keys, key_indices = np.unique(keys, axis=0, return_inverse=True)
    num_keys = len(unique_keys)

    # Perform aggregation
    aggregated_values = _aggregate_with_numba(values, key_indices, measurements, num_keys, num_measurements)

    # Convert results back to original format
    reverse_host_mapping = {v: k for k, v in host_mapping.items()}
    reverse_step_mapping = {v: k for k, v in step_mapping.items()}
    reverse_task_mapping = {v: k for k, v in task_mapping.items()}

    return cast(
        JobMetricData,
        [
            (
                int(unique_key[0]),  # time
                reverse_host_mapping[unique_key[1]],  # host
                reverse_step_mapping[unique_key[2]],  # step
                reverse_task_mapping[unique_key[3]],  # task
                *map(float, aggregated_values[i]),
            )
            for i, unique_key in enumerate(unique_keys)
        ],
    )
