import json
import random
import time
from datetime import datetime
from typing import get_args, cast
from unittest import mock
from collections.abc import Callable, Generator, Iterator
import contextlib

import httpx
import pytest
import respx

from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, SlurmJobData, InfluxDBMeasure
from jobbergate_agent.jobbergate.update import (
    fetch_active_submissions,
    fetch_job_data,
    update_active_jobs,
    update_job_data,
    fetch_influx_data,
    fetch_influx_measurements,
    aggregate_influx_measures,
    update_job_metrics,
)
from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError


@pytest.fixture()
def generate_job_metrics_data() -> Callable[[int, int, int, int, int], Generator[InfluxDBMeasure]]:
    """Generates sample InfluxDB data with multiple points per measurement."""

    def _generate_influxdb_data(
        num_points_per_measurement: int, num_hosts: int, num_jobs: int, num_steps: int, num_tasks: int
    ) -> Generator[InfluxDBMeasure]:
        current_time = int(datetime.now().timestamp())

        for host in range(1, num_hosts + 1):
            for job in range(1, num_jobs + 1):
                for step in range(1, num_steps + 1):
                    for task in range(1, num_tasks + 1):
                        for measurement in get_args(INFLUXDB_MEASUREMENT):
                            for _ in range(num_points_per_measurement):
                                yield {
                                    "time": current_time,
                                    "host": f"host_{host}",
                                    "job": str(job),
                                    "step": str(step),
                                    "task": str(task),
                                    "value": random.random() * 100,
                                    "measurement": measurement,
                                }
                                current_time += random.randint(30, 60)  # increment time by a random interval

    return _generate_influxdb_data


@pytest.fixture()
def aggregate_job_metrics_data():
    """Generates aggregated InfluxDB data with multiple points per measurement."""

    def _aggregate_influxdb_data(
        data_points: Iterator[InfluxDBMeasure],
    ) -> list[tuple[int, str, str, str, float, float, float, float, float, float, float, float, float, float]]:
        measurement_names = get_args(INFLUXDB_MEASUREMENT)
        default_measurements: dict[str, float] = {measurement: 0.0 for measurement in measurement_names}

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

    return _aggregate_influxdb_data


@pytest.fixture()
def job_max_times_response() -> Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]]:
    """Generates a sample response for the endpoint
    ``jobbergate/job-submissions/agent/metrics/<job submission id>``.
    """

    def _job_max_times_response(
        job_submission_id: int, num_hosts: int, num_steps: int, num_tasks: int
    ) -> dict[str, int | list[dict[str, int | str]]]:
        current_time = int(datetime.now().timestamp())
        return {
            "job_submission_id": job_submission_id,
            "max_times": [
                {
                    "max_time": current_time,
                    "node_host": f"host_{host}",
                    "step": step,
                    "task": task,
                }
                for host in range(1, num_hosts + 1)
                for step in range(1, num_steps + 1)
                for task in range(1, num_tasks + 1)
            ],
        }

    return _job_max_times_response


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_job_data__success():
    """
    Test that the ``fetch_job_data()`` function can successfully retrieve
    job data from Slurm as a ``SlurmJobData``.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.return_value = dict(
        job_state="FAILED",
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )

    result: SlurmJobData = await fetch_job_data(123, mocked_sbatch)

    assert result.job_id == 123
    assert result.job_state == "FAILED"
    assert result.state_reason == "NonZeroExitCode"
    assert result.job_info is not None
    assert json.loads(result.job_info) == dict(
        job_state="FAILED",
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_job_data__reports_status_as_UNKOWN_if_slurm_job_id_is_not_found():
    """
    Test that the ``fetch_job_data()`` reports the job state as UNKNOWN if the job matching job id is not found.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.side_effect = RuntimeError("Job not found")

    result: SlurmJobData = await fetch_job_data(123, mocked_sbatch)

    assert result.job_id == 123
    assert result.job_info == "{}"
    assert result.job_state == "UNKNOWN"
    assert result.state_reason == "Slurm did not find a job matching id 123"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__success():
    """
    Test that the ``fetch_active_submissions()`` function can successfully retrieve
    ActiveJobSubmission objects from the API.
    """
    pending_job_submissions_data = {
        "items": [
            dict(
                id=1,
                slurm_job_id=11,
            ),
            dict(
                id=2,
                slurm_job_id=22,
            ),
            dict(
                id=3,
                slurm_job_id=33,
            ),
        ]
    }
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        active_job_submissions = fetch_active_submissions()
        for i, active_job_submission in enumerate(await active_job_submissions):
            assert isinstance(active_job_submission, ActiveJobSubmission)
            assert i + 1 == active_job_submission.id
            assert (i + 1) * 11 == active_job_submission.slurm_job_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__raises_JobbergateApiError_if_response_is_not_200():  # noqa
    """
    Test that the ``fetch_active_submissions()`` function will raise a
    JobbergateApiError if the response from the API is not OK (200).
    """
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(status_code=400)
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch"):
            await fetch_active_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__raises_JobbergateApiError_if_response_cannot_be_deserialized():  # noqa
    """
    Test that the ``fetch_active_submissions()`` function will raise a
    JobbergateApiError if it fails to convert the response to an ActiveJobSubmission.
    """
    active_job_submissions_data = [
        dict(bad="data"),
    ]
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(
                status_code=200,
                json=active_job_submissions_data,
            )
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch active"):
            await fetch_active_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_job_data__success():
    """
    Test that the ``update_job_data()`` can successfully update a job submission with a ``SlurmJobData``.
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await update_job_data(
            1,
            SlurmJobData(
                job_id=13,
                job_state="FAILED",
                job_info="some job info",
                state_reason="Something happened",
            ),
        )

        assert update_route.calls.last.request.content == json.dumps(
            dict(
                slurm_job_id=13,
                slurm_job_state="FAILED",
                slurm_job_info="some job info",
                slurm_job_state_reason="Something happened",
            )
        ).encode("utf-8")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_job_data__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``update_status()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(JobbergateApiError, match="Could not update job data for job submission 1"):
            await update_job_data(
                1,
                SlurmJobData(
                    job_id=13,
                    job_state="FAILED",
                    job_info="some job info",
                    state_reason="Something happened",
                ),
            )
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_active_jobs(
    mocker,
    tweak_settings: Callable[..., contextlib._GeneratorContextManager],
):
    """
    Test that the ``update_active_jobs()`` function can fetch active job submissions,
    retrieve the job data from slurm, and update the slurm job data on the submission via the API.
    """

    mocked_sbatch = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.update.InfoHandler", return_value=mocked_sbatch)

    mocked_influxdb_client = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT", return_value=mocked_influxdb_client)

    active_job_submissions = [
        ActiveJobSubmission(id=1, slurm_job_id=11),  # Will update
        ActiveJobSubmission(id=2, slurm_job_id=22),  # fetch_job_data throws exception
        ActiveJobSubmission(id=3, slurm_job_id=33),  # update_job_data throws exception
    ]

    mocker.patch(
        "jobbergate_agent.jobbergate.update.fetch_active_submissions",
        return_value=active_job_submissions,
    )

    def _mocked_update_job_metrics(active_job_submission: ActiveJobSubmission):
        if active_job_submission.slurm_job_id == 11:
            raise Exception("CRASH!")

    def _mocked_fetch_job_data(slurm_job_id, *args, **kwargs):
        if slurm_job_id == 22:
            raise Exception("BOOM!")
        return {
            11: SlurmJobData(
                job_id=11,
                job_state="FAILED",
                job_info="some job info",
                state_reason="Something happened",
            ),
            33: SlurmJobData(
                job_id=33,
                job_state="COMPLETED",
                job_info="some more job info",
                state_reason="It finished",
            ),
        }[slurm_job_id]

    def _mocked_update_job_data(job_submission_id, slurm_job_data):
        if job_submission_id == 3:
            raise Exception("BANG!")

    mock_update_job_metrics = mocker.patch(
        "jobbergate_agent.jobbergate.update.update_job_metrics", side_effect=_mocked_update_job_metrics
    )
    mock_fetch_job_data = mocker.patch(
        "jobbergate_agent.jobbergate.update.fetch_job_data", side_effect=_mocked_fetch_job_data
    )
    mock_update_job_data = mocker.patch(
        "jobbergate_agent.jobbergate.update.update_job_data", side_effect=_mocked_update_job_data
    )

    with tweak_settings(INFLUX_DSN="https://influxdb:8086"):
        await update_active_jobs()

    mock_update_job_metrics.assert_has_calls(
        [mocker.call(active_job_submission) for active_job_submission in active_job_submissions]
    )
    assert mock_update_job_metrics.call_count == 3

    mock_fetch_job_data.assert_has_calls(
        [mocker.call(11, mocked_sbatch), mocker.call(22, mocked_sbatch), mocker.call(33, mocked_sbatch)]
    )
    assert mock_fetch_job_data.call_count == 3

    mock_update_job_data.assert_has_calls(
        [
            mocker.call(
                1,
                SlurmJobData(
                    job_id=11,
                    job_state="FAILED",
                    job_info="some job info",
                    state_reason="Something happened",
                ),
            ),
            mocker.call(
                3,
                SlurmJobData(
                    job_id=33,
                    job_state="COMPLETED",
                    job_info="some more job info",
                    state_reason="It finished",
                ),
            ),
        ]
    )
    assert mock_update_job_data.call_count == 2


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT")
async def test_fetch_influx_data__success(mocked_influxdb_client: mock.MagicMock):
    """
    Test that the ``fetch_influx_data()`` function can successfully retrieve
    data from InfluxDB as a list of ``InfluxDBMeasure``.
    """
    time = random.randint(0, 1000)  # noqa: F811
    host = "test-host"
    step = random.randint(0, 1000)
    task = random.randint(0, 1000)
    job = random.randint(0, 1000)
    measurement_value = random.uniform(1, 1000)
    measurement = random.choice(get_args(INFLUXDB_MEASUREMENT))

    mocked_influxdb_client.query.return_value.get_points.return_value = [
        dict(
            time=time,
            host=host,
            job=job,
            step=step,
            task=task,
            value=measurement_value,
        )
    ]

    result = await fetch_influx_data(
        time=time,
        host=host,
        step=step,
        task=task,
        job=job,
        measurement=measurement,
    )

    assert len(result) == 1
    assert result[0]["time"] == time
    assert result[0]["host"] == host
    assert result[0]["job"] == job
    assert result[0]["step"] == step
    assert result[0]["task"] == task
    assert result[0]["value"] == measurement_value
    assert result[0]["measurement"] == measurement


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT")
async def test_fetch_influx_data__raises_JobbergateApiError_if_query_fails(mocked_influxdb_client: mock.MagicMock):
    """
    Test that the ``fetch_influx_data()`` function will raise a JobbergateApiError
    if the query to InfluxDB fails.
    """
    measurement = random.choice(get_args(INFLUXDB_MEASUREMENT))

    mocked_influxdb_client.query = mock.Mock(side_effect=Exception("BOOM!"))

    time = random.randint(0, 1000)  # noqa: F811
    host = "test-host"
    step = random.randint(0, 1000)
    task = random.randint(0, 1000)
    job = random.randint(0, 1000)

    query = f"""
    SELECT * FROM {measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
    """
    params = dict(time=time, host=host, step=str(step), task=str(task), job=str(job))

    with pytest.raises(JobbergateApiError, match="Failed to fetch data from InfluxDB"):
        await fetch_influx_data(
            time=time,
            host=host,
            step=step,
            task=task,
            job=job,
            measurement=measurement,
        )

    mocked_influxdb_client.query.assert_called_once_with(query, bind_params=params, epoch="us")


@pytest.mark.asyncio
async def test_fetch_influx_data__raises_JobbergateApiError_if_influxdb_client_is_None():
    """
    Test that the ``fetch_influx_data()`` function will raise a JobbergateApiError
    if the INFLUXDB_CLIENT is None.
    """
    measurement = random.choice(get_args(INFLUXDB_MEASUREMENT))
    with mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT", None):
        with pytest.raises(JobbergateApiError, match="Failed to fetch data from InfluxDB"):
            await fetch_influx_data(
                time=random.randint(0, 1000),
                host="test-host",
                step=random.randint(0, 1000),
                task=random.randint(0, 1000),
                job=random.randint(0, 1000),
                measurement=measurement,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "measurements",
    [
        [{"name": "measurement1"}, {"name": "measurement2"}],
        [{"name": "measurement1"}],
        [],
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT")
async def test_fetch_influx_measurements__success(
    mocked_influxdb_client: mock.MagicMock, measurements: list[dict[str, str]]
):
    """
    Test that the ``fetch_influx_measurements()`` function can successfully retrieve
    measurements from InfluxDB.
    """
    mocked_influxdb_client.get_list_measurements.return_value = measurements

    result = fetch_influx_measurements()

    assert result == measurements


@pytest.mark.asyncio
async def test_fetch_influx_measurements__raises_JobbergateApiError_if_influxdb_client_is_None():
    """
    Test that the ``fetch_influx_measurements()`` function will raise a JobbergateApiError
    if the INFLUXDB_CLIENT is None.
    """
    with mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT", None):
        with pytest.raises(JobbergateApiError, match="Failed to fetch measurements from InfluxDB"):
            fetch_influx_measurements()


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.jobbergate.update.INFLUXDB_CLIENT")
async def test_fetch_influx_measurements__raises_JobbergateApiError_if_query_fails(
    mocked_influxdb_client: mock.MagicMock,
):
    """
    Test that the ``fetch_influx_measurements()`` function will raise a JobbergateApiError
    if the query to InfluxDB fails.
    """
    mocked_influxdb_client.get_list_measurements.side_effect = Exception("BOOM!")

    with pytest.raises(JobbergateApiError, match="Failed to fetch measurements from InfluxDB"):
        fetch_influx_measurements()

    mocked_influxdb_client.get_list_measurements.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "num_points_per_measurement, num_hosts, num_jobs, num_steps, num_tasks",
    [
        (3, 5, 2, 7, 4),
        (1, 1, 1, 1, 1),
        (7, 3, 10, 4, 2),
    ],
)
async def test_aggregate_influx_measures__success(
    num_points_per_measurement: int,
    num_hosts: int,
    num_jobs: int,
    num_steps: int,
    num_tasks: int,
    generate_job_metrics_data: Callable[[int, int, int, int, int], Generator[InfluxDBMeasure]],
    aggregate_job_metrics_data: Callable[
        [Iterator[InfluxDBMeasure]],
        list[tuple[int, str, str, str, float, float, float, float, float, float, float, float, float, float]],
    ],
):
    """
    Test that the ``aggregate_influx_measures()`` function can successfully aggregate
    a list of InfluxDBMeasure data points.
    """
    data_points = list(
        generate_job_metrics_data(
            num_points_per_measurement,
            num_hosts,
            num_jobs,
            num_steps,
            num_tasks,
        )
    )

    start_time = time.monotonic()
    result = aggregate_influx_measures(iter(data_points))
    end_time = time.monotonic()

    expected_result = aggregate_job_metrics_data(iter(data_points))

    assert result == expected_result

    print(f"Aggregated {len(data_points)} data points in {end_time - start_time:.5f} seconds")


@pytest.mark.asyncio
async def test_aggregate_influx_measures__empty_data_points():
    """
    Test that the ``aggregate_influx_measures()`` function returns an empty list
    when given an empty iterator of data points.
    """
    data_points = []

    result = aggregate_influx_measures(iter(data_points))

    assert result == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "job_submission_id, slurm_job_id",
    [
        (1, 22),
        (2, 33),
        (3, 11),
    ],
)
async def test_update_job_metrics__error_getting_metrics_from_api(job_submission_id: int, slurm_job_id: int):
    """
    Test that the ``update_job_metrics()`` function will log an error if it fails
    to get the job metrics from the API.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)

    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}").mock(
            return_value=httpx.Response(status_code=400)
        )

        with pytest.raises(
            JobbergateApiError, match=f"Could not update job metrics for slurm job {slurm_job_id} via the API"
        ):
            await update_job_metrics(active_job_submission)


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "job_submission_id, slurm_job_id, num_hosts, num_steps, num_tasks, measurements",
    [
        (1, 22, 5, 2, 7, [{"name": "measurement1"}, {"name": "measurement2"}]),
        (2, 33, 1, 1, 1, [{"name": "measurement1"}]),
        (3, 11, 3, 10, 4, [{"name": "measurement1"}, {"name": "measurement2"}, {"name": "measurement3"}]),
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_measurements")
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_data")
@mock.patch("jobbergate_agent.jobbergate.update.aggregate_influx_measures")
@mock.patch("jobbergate_agent.jobbergate.update.msgpack")
@mock.patch("jobbergate_agent.jobbergate.update.chain")
async def test_update_job_metrics__error_sending_metrics_to_api(
    mocked_chain: mock.MagicMock,
    mocked_msgpack: mock.MagicMock,
    mocked_aggregate_influx_measures: mock.MagicMock,
    mocked_fetch_influx_data: mock.MagicMock,
    mocked_fetch_influx_measurements: mock.MagicMock,
    job_submission_id: int,
    slurm_job_id: int,
    num_hosts: int,
    num_steps: int,
    num_tasks: int,
    measurements: list[dict[str, str]],
    job_max_times_response: Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]],
):
    """
    Test that the ``update_job_metrics()`` function will log an error if it fails
    to send the job metrics to the API.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)
    job_max_times = job_max_times_response(job_submission_id, num_hosts, num_steps, num_tasks)

    dummy_data_point = {
        "time": 1,
        "host": "host_1",
        "job": "1",
        "step": "1",
        "task": "1",
        "value": 1.0,
        "measurement": "measurement1",
    }
    dummy_data_points = [dummy_data_point] * len(measurements) * len(job_max_times["max_times"])
    iter_dummy_data_points = iter(dummy_data_points)

    mocked_fetch_influx_measurements.return_value = measurements
    mocked_fetch_influx_data.return_value = dummy_data_points
    # doesn't return the real aggregated data due to test complexity
    mocked_chain.from_iterable.return_value = iter_dummy_data_points
    mocked_aggregate_influx_measures.return_value = "super-dummy-aggregated-data"
    mocked_msgpack.packb.return_value = b"dummy-msgpack-data"

    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}").mock(
            return_value=httpx.Response(
                status_code=200,
                json=job_max_times,
            )
        )
        respx.put(
            f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}",
            content=b"dummy-msgpack-data",
        ).mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError, match=f"Could not update job metrics for slurm job {slurm_job_id} via the API"
        ):
            await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [
            mock.call(
                job_max_time["max_time"],
                job_max_time["node_host"],
                job_max_time["step"],
                job_max_time["task"],
                slurm_job_id,
                measurement["name"],
            )
            for job_max_time in job_max_times["max_times"]
            for measurement in measurements
        ]
    )
    mocked_chain.from_iterable.assert_called_once_with(
        [dummy_data_points] * len(measurements) * len(job_max_times["max_times"])
    )
    mocked_aggregate_influx_measures.assert_called_once_with(iter_dummy_data_points)
    mocked_msgpack.packb.assert_called_once_with("super-dummy-aggregated-data")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "job_submission_id, slurm_job_id, num_hosts, num_steps, num_tasks, measurements",
    [
        (1, 22, 5, 2, 7, [{"name": "measurement1"}, {"name": "measurement2"}]),
        (2, 33, 1, 1, 1, [{"name": "measurement1"}]),
        (3, 11, 3, 10, 4, [{"name": "measurement1"}, {"name": "measurement2"}, {"name": "measurement3"}]),
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_measurements")
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_data")
@mock.patch("jobbergate_agent.jobbergate.update.aggregate_influx_measures")
@mock.patch("jobbergate_agent.jobbergate.update.msgpack")
@mock.patch("jobbergate_agent.jobbergate.update.chain")
async def test_update_job_metrics__success(
    mocked_chain: mock.MagicMock,
    mocked_msgpack: mock.MagicMock,
    mocked_aggregate_influx_measures: mock.MagicMock,
    mocked_fetch_influx_data: mock.MagicMock,
    mocked_fetch_influx_measurements: mock.MagicMock,
    job_submission_id: int,
    slurm_job_id: int,
    num_hosts: int,
    num_steps: int,
    num_tasks: int,
    measurements: list[dict[str, str]],
    job_max_times_response: Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]],
):
    """
    Test that the ``update_job_metrics()`` function will log an error if it fails
    to send the job metrics to the API.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)
    job_max_times = job_max_times_response(job_submission_id, num_hosts, num_steps, num_tasks)

    dummy_data_point = {
        "time": 1,
        "host": "host_1",
        "job": "1",
        "step": "1",
        "task": "1",
        "value": 1.0,
        "measurement": "measurement1",
    }
    dummy_data_points = [dummy_data_point] * len(measurements) * len(job_max_times["max_times"])
    iter_dummy_data_points = iter(dummy_data_points)

    mocked_fetch_influx_measurements.return_value = measurements
    mocked_fetch_influx_data.return_value = dummy_data_points
    # doesn't return the real aggregated data due to test complexity
    mocked_chain.from_iterable.return_value = iter_dummy_data_points
    mocked_aggregate_influx_measures.return_value = "super-dummy-aggregated-data"
    mocked_msgpack.packb.return_value = b"dummy-msgpack-data"

    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}").mock(
            return_value=httpx.Response(
                status_code=200,
                json=job_max_times,
            )
        )
        respx.put(
            f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}",
            content=b"dummy-msgpack-data",
        ).mock(return_value=httpx.Response(status_code=200))

        await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [
            mock.call(
                job_max_time["max_time"],
                job_max_time["node_host"],
                job_max_time["step"],
                job_max_time["task"],
                slurm_job_id,
                measurement["name"],
            )
            for job_max_time in job_max_times["max_times"]
            for measurement in measurements
        ]
    )
    mocked_chain.from_iterable.assert_called_once_with(
        [dummy_data_points] * len(measurements) * len(job_max_times["max_times"])
    )
    mocked_aggregate_influx_measures.assert_called_once_with(iter_dummy_data_points)
    mocked_msgpack.packb.assert_called_once_with("super-dummy-aggregated-data")
