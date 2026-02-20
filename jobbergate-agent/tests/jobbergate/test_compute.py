"""Define tests for the functions in jobbergate_agent/utils/compute.py."""

from collections import defaultdict
import pytest
from faker import Faker

from collections.abc import Callable
from datetime import datetime
from typing import cast, get_args
from unittest import mock
import itertools
import numpy as np

from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT
from jobbergate_agent.jobbergate.schemas import InfluxDBPointDict, JobMetricData
from jobbergate_agent.utils.compute import (
    aggregate_influx_measures,
    measure_memory_usage,
    _create_mapping,
    _aggregate_with_numba,
)


def _create_influx_point(
    time: int,
    host: str,
    job: str,
    step: str,
    task: str,
    measurement: str,
    value: float,
) -> InfluxDBPointDict:
    """Create a single InfluxDB point dictionary."""
    return InfluxDBPointDict(
        **{
            "time": time,
            "host": host,
            "job": job,
            "step": step,
            "task": task,
            "value": value,
            "measurement": measurement,
        }
    )


def _generate_measures_for_iteration(
    faker: Faker,
    current_time: int,
    num_hosts: int,
    num_jobs: int,
    num_steps: int,
    num_tasks: int,
    measurement_names: tuple,
) -> tuple[list[InfluxDBPointDict], dict, int]:
    """Generate measures for one iteration and return measures, aggregated data, and updated time."""
    measures = []
    default_measurements: dict[str, float] = dict.fromkeys(measurement_names, 0.0)
    aggregated_data: dict[tuple[int, str, str, str], dict[str, float]] = defaultdict(
        lambda: default_measurements.copy()
    )

    for host, job, step, task in itertools.product(
        range(1, num_hosts + 1),
        range(1, num_jobs + 1),
        range(1, num_steps + 1),
        range(1, num_tasks + 1),
    ):
        time_increment = current_time + (host + job + step - 3) * 10
        key = (time_increment, f"host_{host}", str(step), str(task))

        for measurement in measurement_names:
            value = faker.pyfloat(min_value=0, max_value=100)
            measure = _create_influx_point(
                time=time_increment,
                host=f"host_{host}",
                job=str(job),
                step=str(step),
                task=str(task),
                measurement=measurement,
                value=value,
            )
            measures.append(measure)
            aggregated_data[key][measurement] = value

    return measures, aggregated_data, time_increment


@pytest.fixture()
def generate_and_aggregate_job_metrics_data(
    faker: Faker,
) -> Callable[
    [int, int, int, int, int],
    tuple[
        list[InfluxDBPointDict],
        JobMetricData,
    ],
]:
    """
    Generates sample InfluxDB data and its aggregated counterpart.

    Returns a function that creates both the list of measures and their aggregated version.
    """

    def _generate_and_aggregate(
        num_points_per_measurement: int, num_hosts: int, num_jobs: int, num_steps: int, num_tasks: int
    ) -> tuple[
        list[InfluxDBPointDict],
        JobMetricData,
    ]:
        # Initialize data structures
        current_time = int(datetime.now().timestamp())
        measurement_names = get_args(INFLUXDB_MEASUREMENT)

        all_measures = []
        all_aggregated_data: dict[tuple[int, str, str, str], dict[str, float]] = {}

        # Generate measures for each iteration
        for _ in range(num_points_per_measurement):
            measures, aggregated_data, current_time = _generate_measures_for_iteration(
                faker, current_time, num_hosts, num_jobs, num_steps, num_tasks, measurement_names
            )
            all_measures.extend(measures)
            all_aggregated_data.update(aggregated_data)

        # Create aggregated list
        aggregated_list = cast(
            JobMetricData,
            [
                (
                    time,
                    host,
                    step,
                    task,
                    *(all_aggregated_data[(time, host, step, task)][measurement] for measurement in measurement_names),
                )
                for (time, host, step, task) in all_aggregated_data
            ],
        )

        return all_measures, aggregated_list

    return _generate_and_aggregate


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "num_points_per_measurement, num_hosts, num_jobs, num_steps, num_tasks",
    [
        (1, 1, 1, 1, 1),
        (3, 10, 1, 5, 10),
        (7, 3, 1, 4, 2),
    ],
)
async def test_aggregate_influx_measures__success(
    num_points_per_measurement: int,
    num_hosts: int,
    num_jobs: int,
    num_steps: int,
    num_tasks: int,
    generate_and_aggregate_job_metrics_data: Callable[
        [int, int, int, int, int],
        tuple[
            list[InfluxDBPointDict],
            JobMetricData,
        ],
    ],
):
    """
    Test that the ``aggregate_influx_measures()`` function can successfully aggregate
    a list of InfluxDBPointDict data points.
    """
    measures, expected_aggregated_data = generate_and_aggregate_job_metrics_data(
        num_points_per_measurement, num_hosts, num_jobs, num_steps, num_tasks
    )

    aggregated_data = aggregate_influx_measures(iter(measures))

    for data_point in aggregated_data:
        assert data_point in expected_aggregated_data


@pytest.mark.asyncio
async def test_aggregate_influx_measures__empty_data_points():
    """
    Test that the ``aggregate_influx_measures()`` function returns an empty list
    when given an empty iterator of data points.
    """
    data_points = []

    result = aggregate_influx_measures(iter(data_points))

    assert result == []


@pytest.mark.parametrize(
    "current, peak",
    [(0, 0), (100, 200), (87, 100), (34, 43), (0, 98654), (3245879, 0)],
)
@mock.patch("jobbergate_agent.utils.compute.logger")
@mock.patch("jobbergate_agent.utils.compute.tracemalloc")
def test_measure_memory_usage_decorator(
    mocked_tracemalloc: mock.MagicMock, mocked_logger: mock.MagicMock, current: int, peak: int
):
    """Test the measure_memory_usage decorator."""

    mocked_tracemalloc.get_traced_memory.return_value = (current, peak)

    @measure_memory_usage
    def dummy_function():
        return sum(list(range(10000)))

    result = dummy_function()

    assert result == sum(range(10000))
    mocked_logger.debug.assert_called_once_with(
        f"Memory usage for function '{dummy_function.__name__}': {current=}B, {peak=}B"
    )
    mocked_tracemalloc.start.assert_called_once_with()
    mocked_tracemalloc.get_traced_memory.assert_called_once_with()
    mocked_tracemalloc.stop.assert_called_once_with()


@pytest.mark.parametrize(
    "current, peak",
    [(0, 0), (100, 200), (87, 100), (34, 43), (0, 98654), (3245879, 0)],
)
@mock.patch("jobbergate_agent.utils.compute.logger")
@mock.patch("jobbergate_agent.utils.compute.tracemalloc")
def test_measure_memory_usage_decorator_with_args(
    mocked_tracemalloc: mock.MagicMock, mocked_logger: mock.MagicMock, current: int, peak: int
):
    """Test the measure_memory_usage decorator with arguments."""
    mocked_tracemalloc.get_traced_memory.return_value = (current, peak)

    @measure_memory_usage
    def dummy_function_with_args(a, b):
        return a + b

    result = dummy_function_with_args(5, 10)

    assert result == 15
    mocked_logger.debug.assert_called_once_with(
        f"Memory usage for function '{dummy_function_with_args.__name__}': {current=}B, {peak=}B"
    )
    mocked_tracemalloc.start.assert_called_once_with()
    mocked_tracemalloc.get_traced_memory.assert_called_once_with()
    mocked_tracemalloc.stop.assert_called_once_with()


def test_measure_memory_usage_decorator_logging(caplog):
    """Test the measure_memory_usage decorator logging."""

    @measure_memory_usage
    def dummy_function():
        return sum(list(range(10000)))

    with caplog.at_level("DEBUG"):
        dummy_function()

    assert any("Memory usage for function 'dummy_function'" in message for message in caplog.messages)


def test_create_mapping():
    """Test the _create_mapping function."""
    column = ["apple", "banana", "apple", "orange", "banana", "apple"]
    expected_mapping = {"apple": 0, "banana": 1, "orange": 2}

    result = _create_mapping(column)

    assert result == expected_mapping


def test_create_mapping_empty():
    """Test the _create_mapping function with an empty list."""
    column = []
    expected_mapping = {}

    result = _create_mapping(column)

    assert result == expected_mapping


def test_create_mapping_single_value():
    """Test the _create_mapping function with a single value list."""
    column = ["apple"]
    expected_mapping = {"apple": 0}

    result = _create_mapping(column)

    assert result == expected_mapping


def test_create_mapping_multiple_unique_values():
    """Test the _create_mapping function with multiple unique values."""
    column = ["apple", "banana", "cherry", "date"]
    expected_mapping = {"apple": 0, "banana": 1, "cherry": 2, "date": 3}

    result = _create_mapping(column)

    assert result == expected_mapping


def test_aggregate_with_numba():
    """Test the _aggregate_with_numba function."""
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    key_indices = np.array([0, 1, 0, 1, 0])
    measurement_indices = np.array([0, 0, 1, 1, 0])
    num_keys = 2
    num_measurements = 2

    expected_aggregated_values = np.array([[6.0, 3.0], [2.0, 4.0]])

    result = _aggregate_with_numba(values, key_indices, measurement_indices, num_keys, num_measurements)

    np.testing.assert_array_equal(result, expected_aggregated_values)


def test_aggregate_with_numba_single_value():
    """Test the _aggregate_with_numba function with a single value."""
    values = np.array([1.0])
    key_indices = np.array([0])
    measurement_indices = np.array([0])
    num_keys = 1
    num_measurements = 1

    expected_aggregated_values = np.array([[1.0]])

    result = _aggregate_with_numba(values, key_indices, measurement_indices, num_keys, num_measurements)

    np.testing.assert_array_equal(result, expected_aggregated_values)


def test_aggregate_with_numba_multiple_measurements():
    """Test the _aggregate_with_numba function with multiple measurements."""
    values = np.array([1.0, 2.0, 3.0, 4.0])
    key_indices = np.array([0, 0, 1, 1])
    measurement_indices = np.array([0, 1, 0, 1])
    num_keys = 2
    num_measurements = 2

    expected_aggregated_values = np.array([[1.0, 2.0], [3.0, 4.0]])

    result = _aggregate_with_numba(values, key_indices, measurement_indices, num_keys, num_measurements)

    np.testing.assert_array_equal(result, expected_aggregated_values)
