"""
Provide command for generating dummy job metrics for testing purposes.
"""

import random
from collections.abc import Iterator
from datetime import datetime
from typing import cast, Generator, get_args, Literal, TypedDict

import typer
import msgpack

app = typer.Typer()


INFLUXDB_MEASUREMENT = Literal[
    "CPUFrequency",
    "CPUTime",
    "CPUUtilization",
    "GPUMemMB",
    "GPUUtilization",
    "Pages",
    "RSS",
    "ReadMB",
    "VMSize",
    "WriteMB",
]

INFLUXDB_MEASUREMENT_TYPES = {
    "CPUFrequency": int,
    "CPUTime": float,
    "CPUUtilization": float,
    "GPUMemMB": int,
    "GPUUtilization": float,
    "Pages": int,
    "RSS": int,
    "ReadMB": int,
    "VMSize": int,
    "WriteMB": int,
}


class InfluxDBMeasure(TypedDict):
    """
    Map each entry in the generator returned by InfluxDBClient(...).query(...).get_points().
    """

    time: int
    host: str
    job: str
    step: str
    task: str
    value: float
    measurement: INFLUXDB_MEASUREMENT


def _generate_influxdb_data(
    num_points_per_measurement: int, num_hosts: int, num_jobs: int, num_steps: int, num_tasks: int
) -> Generator[InfluxDBMeasure, None, None]:
    current_time = int(datetime.now().timestamp())

    for _ in range(num_points_per_measurement):
        for host in range(1, num_hosts + 1):
            for job in range(1, num_jobs + 1):
                for step in range(1, num_steps + 1):
                    for task in range(1, num_tasks + 1):
                        for measurement in get_args(INFLUXDB_MEASUREMENT):
                            yield {
                                "time": current_time,
                                "host": f"host_{host}",
                                "job": str(job),
                                "step": str(step),
                                "task": str(task),
                                "value": INFLUXDB_MEASUREMENT_TYPES[measurement](random.random() * 100),
                                "measurement": measurement,
                            }
        current_time += 10


def _aggregate_influxdb_data(
    data_points: Iterator[InfluxDBMeasure],
) -> list[tuple[int, str, str, str, float, float, float, float, float, float, float, float, float, float]]:
    measurement_names = get_args(INFLUXDB_MEASUREMENT)
    default_measurements: dict[str, float] = dict.fromkeys(measurement_names, 0.0)

    aggregated_data: dict[tuple[int, str, str, str], dict[str, float]] = {}

    for measure in data_points:
        key = (measure["time"], measure["host"], measure["step"], measure["task"])

        # aggregate measurements lazily to avoid creating a new dict for each point
        if key not in aggregated_data:
            aggregated_data[key] = default_measurements.copy()
        aggregated_data[key][measure["measurement"]] = measure["value"]

    return cast(
        list[tuple[int, str, str, str, float, float, float, float, float, float, float, float, float, float]],
        [
            (
                time,
                host,
                step,
                task,
                *(aggregated_data[(time, host, step, task)][measurement] for measurement in measurement_names),
            )
            for (time, host, step, task) in aggregated_data
        ],
    )


@app.command()
def generate_metrics(
    num_points_per_measurement: int = typer.Option(5, help="Number of data points per measurement."),
    num_hosts: int = typer.Option(5, help="Number of hosts to generate metrics for."),
    num_jobs: int = typer.Option(5, help="Number of jobs to generate metrics for."),
    num_steps: int = typer.Option(5, help="Number of steps to generate metrics for."),
    num_tasks: int = typer.Option(5, help="Number of tasks to generate metrics for."),
    path: str = typer.Option("dummy_metrics.msgpack", help="Path to write the generated metrics."),
):
    """
    Generate dummy job metrics for a given job submission.
    """
    data_points = _generate_influxdb_data(num_points_per_measurement, num_hosts, num_jobs, num_steps, num_tasks)
    aggregated_data = _aggregate_influxdb_data(data_points)
    binary_data: bytes = msgpack.packb(aggregated_data)

    with open(path, "wb") as f:
        f.write(binary_data)
