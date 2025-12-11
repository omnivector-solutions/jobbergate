import json
from pathlib import Path
import uuid
from collections.abc import Callable
from datetime import datetime
from itertools import combinations
from textwrap import dedent
from typing import Any, NamedTuple, get_args
from unittest import mock

import httpx
import pytest
import respx
from faker import Faker

from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT, JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, SlurmJobData
from jobbergate_agent.jobbergate.update import (
    ActiveSubmissionContext,
    active_job_cancellation_strategy,
    active_submission_plugin_manager,
    empty_strategy,
    fetch_active_submissions,
    fetch_influx_data,
    fetch_influx_measurements,
    fetch_job_data,
    job_data_update_strategy,
    job_metrics_strategy,
    pending_job_cancellation_strategy,
    update_active_jobs,
    update_job_data,
    update_job_metrics,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateAgentError, JobbergateApiError, SbatchError


@pytest.fixture()
def job_max_times_response() -> Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]]:
    """Generates a sample response for the endpoint
    ``jobbergate/job-submissions/agent/metrics/<job submission id>``.
    """

    def _job_max_times_response(
        job_submission_id: int, num_hosts: int, num_steps: int, num_tasks: int
    ) -> dict[str, int | list[dict[str, int | str]]]:
        current_time = int(datetime.now().timestamp())
        max_times_list: list[dict[str, int | str]] = [
            {
                "max_time": current_time,
                "node_host": f"host_{host}",
                "step": step,
                "task": task,
            }
            for host in range(1, num_hosts + 1)
            for step in range(1, num_steps + 1)
            for task in range(1, num_tasks + 1)
        ]
        return {
            "job_submission_id": job_submission_id,
            "max_times": max_times_list,
        }

    return _job_max_times_response


@pytest.mark.usefixtures("mock_access_token")
def test_fetch_job_data__success():
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

    result: SlurmJobData = fetch_job_data(123, mocked_sbatch)

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


@pytest.mark.usefixtures("mock_access_token")
def test_fetch_job_data__handles_list_in_job_state():
    """
    Test that the ``fetch_job_data()`` function can successfully retrieve
    job data from Slurm as a ``SlurmJobData`` when the job_state from slurm
    is reported as a list.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.return_value = dict(
        job_state=["FAILED"],
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )

    result: SlurmJobData = fetch_job_data(123, mocked_sbatch)

    assert result.job_id == 123
    assert result.job_state == "FAILED"
    assert result.state_reason == "NonZeroExitCode"
    assert result.job_info is not None
    assert json.loads(result.job_info) == dict(
        job_state=["FAILED"],
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_job_data__raises_error_if_job_state_is_invalid_list():
    """
    Test that the ``fetch_job_data()`` function raises an exception
    if the list slurm_job_state does not have at least one value.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.return_value = dict(
        job_state=[],
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )

    with pytest.raises(SbatchError, match="does not have at least one value"):
        await fetch_job_data(123, mocked_sbatch)


@pytest.mark.usefixtures("mock_access_token")
def test_fetch_job_data__reports_status_as_unknown_if_slurm_job_id_is_not_found():
    """
    Test that the ``fetch_job_data()`` reports the job state as UNKNOWN if the job matching job id is not found.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.side_effect = RuntimeError("Job not found")

    result: SlurmJobData = fetch_job_data(123, mocked_sbatch)

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
        ],
        "page": 1,
        "pages": 1,
        "size": 3,
        "total": 3,
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

        assert json.loads(update_route.calls.last.request.content) == dict(
            slurm_job_id=13,
            slurm_job_state="FAILED",
            slurm_job_info="some job info",
            slurm_job_state_reason="Something happened",
        )


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
async def test_update_active_jobs():
    """
    Test that the ``update_active_jobs()`` function can fetch active job submissions
    and execute the appropriate strategies based on job state and conditions.
    """
    # Setup mock data
    mock_submissions = [
        ActiveJobSubmission(id=1, slurm_job_id=100, status="ACTIVE"),
        ActiveJobSubmission(id=2, slurm_job_id=101, status="ACTIVE"),
    ]

    # Mock strategies
    mock_strategy_1 = mock.AsyncMock()
    mock_strategy_2 = mock.AsyncMock()

    # Mock plugin manager
    mock_pm = mock.Mock()
    mock_pm.hook.active_submission.return_value = [mock_strategy_1, mock_strategy_2]

    with (
        mock.patch("jobbergate_agent.jobbergate.update.active_submission_plugin_manager", return_value=mock_pm),
        mock.patch("jobbergate_agent.jobbergate.update.fetch_active_submissions", return_value=mock_submissions),
    ):
        await update_active_jobs()

        # Verify fetch was called
        assert mock_pm.hook.active_submission.call_count == 2

        # Verify strategies were executed for each job
        assert mock_strategy_1.call_count == 2
        assert mock_strategy_2.call_count == 2


@pytest.mark.asyncio
async def test_update_active_jobs_handles_exceptions():
    """Test that exceptions in strategy execution are caught and logged."""
    mock_submissions = [ActiveJobSubmission(id=1, slurm_job_id=100, status="ACTIVE")]

    # Create a strategy that raises an exception
    async def failing_strategy():
        raise ValueError("Test error")

    mock_pm = mock.Mock()
    mock_pm.hook.active_submission.return_value = [failing_strategy]

    with (
        mock.patch("jobbergate_agent.jobbergate.update.active_submission_plugin_manager", return_value=mock_pm),
        mock.patch("jobbergate_agent.jobbergate.update.fetch_active_submissions", return_value=mock_submissions),
    ):
        # Should not raise - exceptions are caught
        await update_active_jobs()


@pytest.mark.asyncio
async def test_update_active_jobs_empty_list():
    """Test handling of empty submission list."""
    mock_pm = mock.Mock()

    with (
        mock.patch("jobbergate_agent.jobbergate.update.active_submission_plugin_manager", return_value=mock_pm),
        mock.patch("jobbergate_agent.jobbergate.update.fetch_active_submissions", return_value=[]),
    ):
        await update_active_jobs()

        # Hook should not be called for empty list
        mock_pm.hook.active_submission.assert_not_called()


class InfluxData(NamedTuple):
    time: int
    host: str
    step: int
    task: int
    job: int
    value: float
    measurement: INFLUXDB_MEASUREMENT

    def fetch_data_kwargs(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "host": self.host,
            "step": self.step,
            "task": self.task,
            "job": self.job,
            "measurement": self.measurement,
        }

    def query_return_value(self) -> dict[str, Any]:
        return {k: v for k, v in self._asdict().items() if k != "measurement"}

    def bind_params(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "host": self.host,
            "step": str(self.step),
            "task": str(self.task),
            "job": str(self.job),
        }


@pytest.fixture()
def influx_data(faker: Faker) -> InfluxData:
    """Generates a sample InfluxDB data point."""
    return InfluxData(
        time=faker.random_int(min=0, max=1000),
        host=faker.word(),
        step=faker.random_int(min=0, max=1000),
        task=faker.random_int(min=0, max=1000),
        job=faker.random_int(min=0, max=1000),
        value=faker.pyfloat(min_value=1, max_value=1000),
        measurement=faker.random_element(get_args(INFLUXDB_MEASUREMENT)),
    )


@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
def test_fetch_influx_data__success_with_all_set(mocked_influxdb_client: mock.MagicMock, influx_data: InfluxData):
    """
    Test that the ``fetch_influx_data()`` function can successfully retrieve
    data from InfluxDB as a list of ``InfluxDBPointDict`` when all arguments
    are passed.
    """
    mocked_influxdb_client.query.return_value.get_points.return_value = [influx_data.query_return_value()]

    query = dedent(f"""
    SELECT * FROM {influx_data.measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
    """)

    result = fetch_influx_data(**influx_data.fetch_data_kwargs())

    assert len(result) == 1
    assert result[0] == influx_data._asdict()

    mocked_influxdb_client.query.assert_called_once_with(query, bind_params=influx_data.bind_params(), epoch="s")


@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
def test_fetch_influx_data__data_point_overflow(mocked_influxdb_client: mock.MagicMock, influx_data: InfluxData):
    """
    Test that the ``fetch_influx_data()`` function prevents a overflow
    when the data point value cannot be stored in disk as an int64.
    """
    influx_data = influx_data._replace(value=influx_data.value + 2**63 - 1)  # cause overflow

    mocked_influxdb_client.query.return_value.get_points.return_value = [influx_data.query_return_value()]

    query = dedent(f"""
    SELECT * FROM {influx_data.measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
    """)

    result = fetch_influx_data(**influx_data.fetch_data_kwargs())

    assert len(result) == 1
    assert result[0] == influx_data._replace(value=0)._asdict()
    mocked_influxdb_client.query.assert_called_once_with(query, bind_params=influx_data.bind_params(), epoch="s")


@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
async def test_fetch_influx_data__success_with_all_None(
    mocked_influxdb_client: mock.MagicMock, faker: Faker, influx_data: InfluxData
):
    """
    Test that the ``fetch_influx_data()`` function can successfully retrieve
    data from InfluxDB as a list of ``InfluxDBPointDict`` when some arguments
    are None.
    """
    mocked_influxdb_client.query.return_value.get_points.return_value = [influx_data.query_return_value()]

    query = f"SELECT * FROM {influx_data.measurement} WHERE job = $job"
    params = {"job": str(influx_data.job)}

    result = fetch_influx_data(influx_data.job, influx_data.measurement)

    assert len(result) == 1
    assert result[0] == influx_data._asdict()
    mocked_influxdb_client.query.assert_called_once_with(query, bind_params=params, epoch="s")


@pytest.mark.parametrize(
    "time, host, step, task",
    [
        tuple(1 if i not in combination else None for i in range(4))
        for r in range(1, 4)
        for combination in combinations(range(4), r)
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
def test_fetch_influx_data__raises_jobbergate_agent_error_if_bad_arguments_are_passed(
    mocked_influxdb_client: mock.MagicMock,
    time: int | None,
    host: int | None,
    step: int | None,
    task: int | None,
    faker: Faker,
):
    job = faker.random_int(min=0, max=100)
    measurement = faker.random_element(get_args(INFLUXDB_MEASUREMENT))

    with pytest.raises(
        JobbergateAgentError, match="Invalid argument combination: all optional arguments must be either set or None."
    ):
        fetch_influx_data(
            job,
            measurement,
            time=time,
            host=str(host) if host is not None else None,
            step=step,
            task=task,
        )

    mocked_influxdb_client.query.assert_not_called()


@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
def test_fetch_influx_data__raises_jobbergate_agent_error_if_query_fails(
    mocked_influxdb_client: mock.MagicMock, influx_data: InfluxData
):
    """
    Test that the ``fetch_influx_data()`` function will raise a JobbergateAgentError
    if the query to InfluxDB fails.
    """
    mocked_influxdb_client.query = mock.Mock(side_effect=Exception("BOOM!"))

    query = dedent(f"""
    SELECT * FROM {influx_data.measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
    """)

    with pytest.raises(JobbergateAgentError, match="Failed to fetch measures from InfluxDB -- Exception: BOOM!"):
        fetch_influx_data(**influx_data.fetch_data_kwargs())

    mocked_influxdb_client.query.assert_called_once_with(query, bind_params=influx_data.bind_params(), epoch="s")


def test_fetch_influx_data__raises_jobbergate_agent_error_if_influxdb_client_is_none(influx_data: InfluxData):
    """
    Test that the ``fetch_influx_data()`` function will raise a JobbergateAgentError
    if the influxdb_client is None.
    """
    with mock.patch("jobbergate_agent.jobbergate.update.influxdb_client", None):
        with pytest.raises(JobbergateAgentError, match="Failed to fetch measures from InfluxDB -- AssertionError:"):
            fetch_influx_data(**influx_data.fetch_data_kwargs())


@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
def test_fetch_influx_measurements__success(mocked_influxdb_client: mock.MagicMock, faker: Faker):
    """
    Test that the ``fetch_influx_measurements()`` function can successfully retrieve
    measurements from InfluxDB.
    """
    expected_measurements = [{"name": measurement} for measurement in get_args(INFLUXDB_MEASUREMENT)]
    extended_measurements = expected_measurements + [
        {"name": str(uuid.uuid4())} for _ in range(1, faker.random_int(min=2, max=11))
    ]

    mocked_influxdb_client.get_list_measurements.return_value = extended_measurements

    result = fetch_influx_measurements()

    assert result == expected_measurements


@pytest.mark.asyncio
async def test_fetch_influx_measurements__raises_JobbergateApiError_if_influxdb_client_is_None():
    """
    Test that the ``fetch_influx_measurements()`` function will raise a JobbergateApiError
    if the influxdb_client is None.
    """
    with mock.patch("jobbergate_agent.jobbergate.update.influxdb_client", None):
        with pytest.raises(JobbergateApiError, match="Failed to fetch measurements from InfluxDB"):
            fetch_influx_measurements()


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.jobbergate.update.influxdb_client")
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

    # Type assertion to help mypy
    assert isinstance(job_max_times["max_times"], list)
    max_times_list = job_max_times["max_times"]

    dummy_data_point = {
        "time": 1,
        "host": "host_1",
        "job": "1",
        "step": "1",
        "task": "1",
        "value": 1.0,
        "measurement": "measurement1",
    }
    dummy_data_points = [dummy_data_point] * len(measurements) * len(max_times_list)
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
            headers={"Content-Type": "application/octet-stream"},
        ).mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError, match=f"Could not update job metrics for slurm job {slurm_job_id} via the API"
        ):
            await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [
            mock.call(
                slurm_job_id,
                measurement["name"],
                time=int(job_max_time["max_time"] * 1e9),  # type: ignore
                host=job_max_time["node_host"],
                step=job_max_time["step"],
                task=job_max_time["task"],
            )
            for job_max_time in max_times_list
            for measurement in measurements
        ]
    )
    mocked_chain.from_iterable.assert_called_once_with([dummy_data_points] * len(measurements) * len(max_times_list))
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
    Test that the ``update_job_metrics()`` function will execute its logic properly
    when the API requests are un.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)
    job_max_times = job_max_times_response(job_submission_id, num_hosts, num_steps, num_tasks)

    # Type assertion to help mypy
    assert isinstance(job_max_times["max_times"], list)
    max_times_list = job_max_times["max_times"]

    dummy_data_point = {
        "time": 1,
        "host": "host_1",
        "job": "1",
        "step": "1",
        "task": "1",
        "value": 1.0,
        "measurement": "measurement1",
    }
    dummy_data_points = [dummy_data_point] * len(measurements) * len(max_times_list)
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
            headers={"Content-Type": "application/octet-stream"},
        ).mock(return_value=httpx.Response(status_code=200))

        await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [
            mock.call(
                slurm_job_id,
                measurement["name"],
                time=int(job_max_time["max_time"] * 1e9),  # type: ignore
                host=job_max_time["node_host"],
                step=job_max_time["step"],
                task=job_max_time["task"],
            )
            for job_max_time in max_times_list
            for measurement in measurements
        ]
    )
    mocked_chain.from_iterable.assert_called_once_with([dummy_data_points] * len(measurements) * len(max_times_list))
    mocked_aggregate_influx_measures.assert_called_once_with(iter_dummy_data_points)
    mocked_msgpack.packb.assert_called_once_with("super-dummy-aggregated-data")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "job_submission_id, slurm_job_id, measurements",
    [
        (1, 22, [{"name": "measurement1"}, {"name": "measurement2"}]),
        (2, 33, [{"name": "measurement1"}]),
        (3, 11, [{"name": "measurement1"}, {"name": "measurement2"}, {"name": "measurement3"}]),
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_measurements")
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_data")
@mock.patch("jobbergate_agent.jobbergate.update.aggregate_influx_measures")
@mock.patch("jobbergate_agent.jobbergate.update.msgpack")
@mock.patch("jobbergate_agent.jobbergate.update.chain")
async def test_update_job_metrics__success_with_max_times_empty(
    mocked_chain: mock.MagicMock,
    mocked_msgpack: mock.MagicMock,
    mocked_aggregate_influx_measures: mock.MagicMock,
    mocked_fetch_influx_data: mock.MagicMock,
    mocked_fetch_influx_measurements: mock.MagicMock,
    job_submission_id: int,
    slurm_job_id: int,
    measurements: list[dict[str, str]],
    job_max_times_response: Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]],
):
    """
    Test that the ``update_job_metrics()`` function will execute the proper logic when
    the API response to get the `max_times` is empty.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)
    job_max_times = job_max_times_response(job_submission_id, 0, 0, 0)

    dummy_data_point = {
        "time": 1,
        "host": "host_1",
        "job": "1",
        "step": "1",
        "task": "1",
        "value": 1.0,
        "measurement": "measurement1",
    }
    dummy_data_points = [dummy_data_point] * len(measurements)
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
            headers={"Content-Type": "application/octet-stream"},
        ).mock(return_value=httpx.Response(status_code=200))

        await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [mock.call(slurm_job_id, measurement["name"]) for measurement in measurements]
    )
    mocked_chain.from_iterable.assert_called_once_with([dummy_data_points] * len(measurements))
    mocked_aggregate_influx_measures.assert_called_once_with(iter_dummy_data_points)
    mocked_msgpack.packb.assert_called_once_with("super-dummy-aggregated-data")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "job_submission_id, slurm_job_id, measurements",
    [
        (1, 22, [{"name": "measurement1"}, {"name": "measurement2"}]),
        (2, 33, [{"name": "measurement1"}]),
        (3, 11, [{"name": "measurement1"}, {"name": "measurement2"}, {"name": "measurement3"}]),
    ],
)
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_measurements")
@mock.patch("jobbergate_agent.jobbergate.update.fetch_influx_data")
@mock.patch("jobbergate_agent.jobbergate.update.aggregate_influx_measures")
@mock.patch("jobbergate_agent.jobbergate.update.msgpack")
@mock.patch("jobbergate_agent.jobbergate.update.chain")
async def test_update_job_metrics__defer_api_call_upon_no_new_data(
    mocked_chain: mock.MagicMock,
    mocked_msgpack: mock.MagicMock,
    mocked_aggregate_influx_measures: mock.MagicMock,
    mocked_fetch_influx_data: mock.MagicMock,
    mocked_fetch_influx_measurements: mock.MagicMock,
    job_submission_id: int,
    slurm_job_id: int,
    measurements: list[dict[str, str]],
    job_max_times_response: Callable[[int, int, int, int], dict[str, int | list[dict[str, int | str]]]],
):
    """
    Test that the ``update_job_metrics()`` function will defer sending data to the API
    when there's no new data to send.
    """
    active_job_submission = ActiveJobSubmission(id=job_submission_id, slurm_job_id=slurm_job_id)
    job_max_times = job_max_times_response(job_submission_id, 0, 0, 0)

    mocked_fetch_influx_measurements.return_value = measurements
    mocked_fetch_influx_data.return_value = []
    mocked_chain.from_iterable.return_value = []
    mocked_aggregate_influx_measures.return_value = []

    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/metrics/{job_submission_id}").mock(
            return_value=httpx.Response(
                status_code=200,
                json=job_max_times,
            )
        )

        await update_job_metrics(active_job_submission)

    mocked_fetch_influx_measurements.assert_called_once_with()
    mocked_fetch_influx_data.assert_has_calls(
        [mock.call(slurm_job_id, measurement["name"]) for measurement in measurements]
    )
    mocked_chain.from_iterable.assert_called_once_with([[] for _ in range(len(measurements))])
    mocked_aggregate_influx_measures.assert_called_once_with([])
    mocked_msgpack.packb.assert_not_called()


class TestPendingJobCancellationStrategy:
    """Tests for PendingJobCancellationStrategy."""

    def test_need_to_run__returns_true_when_job_is_cancelled_with_no_slurm_job_id(self):
        """Test that need_to_run returns True for cancelled jobs with no slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=None,
        )
        strategy = pending_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is not empty_strategy

    def test_need_to_run__returns_false_when_job_has_slurm_job_id(self):
        """Test that need_to_run returns False for cancelled jobs with a slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=123,
        )
        strategy = pending_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    def test_need_to_run__returns_false_when_job_is_not_cancelled(self):
        """Test that need_to_run returns False for non-cancelled jobs."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",  # Using string instead of enum
            slurm_job_id=None,
        )
        strategy = pending_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    @pytest.mark.asyncio
    async def test_run__updates_job_data_with_cancelled_state(self, mocker):
        """Test that run method updates job data with cancelled state."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=None,
        )
        strategy = pending_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))

        mock_update_job_data = mocker.patch("jobbergate_agent.jobbergate.update.update_job_data")

        await strategy()

        mock_update_job_data.assert_called_once_with(
            1,
            SlurmJobData(
                job_state="CANCELLED",
                state_reason="Job was cancelled by the user before a slurm job was created",
            ),
        )


class TestActiveJobCancellationStrategy:
    """Tests for ActiveJobCancellationStrategy."""

    def test_need_to_run__returns_true_when_job_is_cancelled_with_slurm_job_id(self):
        """Test that need_to_run returns True for cancelled jobs with a slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=123,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is not empty_strategy

    def test_need_to_run__returns_false_when_job_has_no_slurm_job_id(self):
        """Test that need_to_run returns False for cancelled jobs without a slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=None,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    def test_need_to_run__returns_false_when_job_is_not_cancelled(self):
        """Test that need_to_run returns False for non-cancelled jobs."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",  # Using string instead of enum
            slurm_job_id=123,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    @pytest.mark.asyncio
    async def test_run__cancels_slurm_job_successfully(self, mocker):
        """Test that run method successfully cancels a slurm job."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=123,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))

        mock_scancel_handler = mocker.Mock()
        mock_scancel_class = mocker.patch(
            "jobbergate_agent.jobbergate.update.ScancelHandler", return_value=mock_scancel_handler
        )

        await strategy()

        mock_scancel_class.assert_called_once_with(scancel_path=SETTINGS.SCANCEL_PATH)
        mock_scancel_handler.cancel_job.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_run__handles_runtime_error_when_canceling_job(self, mocker):
        """Test that run method handles RuntimeError when canceling a job."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=123,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))

        mock_scancel_handler = mocker.Mock()
        mock_scancel_handler.cancel_job.side_effect = RuntimeError("Slurm error")
        mocker.patch("jobbergate_agent.jobbergate.update.ScancelHandler", return_value=mock_scancel_handler)

        # Should not raise an exception
        await strategy()

        mock_scancel_handler.cancel_job.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_run__returns_early_when_slurm_job_id_is_none(self, mocker):
        """Test that run method returns early when slurm_job_id is None."""
        job_submission = ActiveJobSubmission(
            id=1,
            status=JobSubmissionStatus.CANCELLED,
            slurm_job_id=None,
        )
        strategy = active_job_cancellation_strategy(ActiveSubmissionContext(data=job_submission))

        mock_scancel_class = mocker.patch("jobbergate_agent.jobbergate.update.ScancelHandler")

        await strategy()

        mock_scancel_class.assert_not_called()


class TestJobMetricsStrategy:
    """Tests for JobMetricsStrategy."""

    def test_need_to_run__returns_true_when_influx_enabled_and_has_slurm_job_id(self, tweak_settings):
        """Test that need_to_run returns True when influx is enabled and job has slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )

        with tweak_settings(INFLUX_DSN="http://localhost:8086"):
            strategy = job_metrics_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is not empty_strategy

    def test_need_to_run__returns_false_when_influx_disabled(self, tweak_settings):
        """Test that need_to_run returns False when influx integration is disabled."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )

        with tweak_settings(INFLUX_DSN=None):
            strategy = job_metrics_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    def test_need_to_run__returns_false_when_no_slurm_job_id(self, tweak_settings):
        """Test that need_to_run returns False when job has no slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=None,
        )

        with tweak_settings(INFLUX_DSN="http://localhost:8086"):
            strategy = job_metrics_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    @pytest.mark.asyncio
    async def test_run__calls_update_job_metrics(self, mocker, tweak_settings):
        """Test that run method calls update_job_metrics."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )

        with tweak_settings(INFLUX_DSN="http://localhost:8086"):
            strategy = job_metrics_strategy(ActiveSubmissionContext(data=job_submission))

        mock_update_job_metrics = mocker.patch("jobbergate_agent.jobbergate.update.update_job_metrics")

        await strategy()

        mock_update_job_metrics.assert_called_once_with(job_submission)

    @pytest.mark.asyncio
    async def test_run__handles_exception_from_update_job_metrics(self, mocker, tweak_settings):
        """Test that run method handles exceptions from update_job_metrics."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )

        with tweak_settings(INFLUX_DSN="http://localhost:8086"):
            strategy = job_metrics_strategy(ActiveSubmissionContext(data=job_submission))

        mock_update_job_metrics = mocker.patch(
            "jobbergate_agent.jobbergate.update.update_job_metrics", side_effect=Exception("Metrics update failed")
        )

        # Should not raise an exception
        await strategy()

        mock_update_job_metrics.assert_called_once_with(job_submission)


class TestJobDataUpdateStrategy:
    """Tests for JobDataUpdateStrategy."""

    def test_need_to_run__returns_true_when_has_slurm_job_id(self):
        """Test that need_to_run returns True when job has slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is not empty_strategy

    def test_need_to_run__returns_false_when_no_slurm_job_id(self):
        """Test that need_to_run returns False when job has no slurm_job_id."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=None,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))
        assert strategy is empty_strategy

    @pytest.mark.asyncio
    async def test_run__fetches_and_updates_job_data_successfully(self, mocker):
        """Test that run method fetches and updates job data successfully."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))

        mock_info_handler = mocker.Mock()
        mock_info_class = mocker.patch("jobbergate_agent.jobbergate.update.InfoHandler", return_value=mock_info_handler)

        slurm_job_data = SlurmJobData(
            job_id=123,
            job_state="COMPLETED",
            job_info="{}",
            state_reason="Job completed successfully",
        )
        mock_fetch_job_data = mocker.patch(
            "jobbergate_agent.jobbergate.update.fetch_job_data", return_value=slurm_job_data
        )
        mock_update_job_data = mocker.patch("jobbergate_agent.jobbergate.update.update_job_data")

        await strategy()

        mock_info_class.assert_called_once_with(scontrol_path=SETTINGS.SCONTROL_PATH)
        mock_fetch_job_data.assert_called_once_with(123, mock_info_handler)
        mock_update_job_data.assert_called_once_with(1, slurm_job_data)

    @pytest.mark.asyncio
    async def test_run__handles_exception_from_fetch_job_data(self, mocker):
        """Test that run method handles exceptions from fetch_job_data."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))

        mock_info_handler = mocker.Mock()
        mocker.patch("jobbergate_agent.jobbergate.update.InfoHandler", return_value=mock_info_handler)
        mocker.patch("jobbergate_agent.jobbergate.update.fetch_job_data", side_effect=Exception("Fetch failed"))
        mock_update_job_data = mocker.patch("jobbergate_agent.jobbergate.update.update_job_data")

        await strategy()

        # Should not call update_job_data when fetch_job_data fails
        mock_update_job_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_run__handles_exception_from_update_job_data(self, mocker):
        """Test that run method handles exceptions from update_job_data."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=123,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))

        mock_info_handler = mocker.Mock()
        mocker.patch("jobbergate_agent.jobbergate.update.InfoHandler", return_value=mock_info_handler)

        slurm_job_data = SlurmJobData(
            job_id=123,
            job_state="COMPLETED",
            job_info="{}",
            state_reason="Job completed successfully",
        )
        mocker.patch("jobbergate_agent.jobbergate.update.fetch_job_data", return_value=slurm_job_data)
        mocker.patch("jobbergate_agent.jobbergate.update.update_job_data", side_effect=Exception("Update failed"))

        # Should not raise an exception
        await strategy()

    @pytest.mark.asyncio
    async def test_run__returns_early_when_slurm_job_id_is_none(self, mocker):
        """Test that run method returns early when slurm_job_id is None."""
        job_submission = ActiveJobSubmission(
            id=1,
            status="CREATED",
            slurm_job_id=None,
        )
        strategy = job_data_update_strategy(ActiveSubmissionContext(data=job_submission))

        mock_info_class = mocker.patch("jobbergate_agent.jobbergate.update.InfoHandler")

        await strategy()

        mock_info_class.assert_not_called()


class TestUpdateActiveJobsStrategies:
    """Test how update_active_jobs works with the strategy pattern."""

    def test_update_gets_all_strategies(self):
        """Test that update_active_jobs retrieves all defined strategies."""
        plugin_manager = active_submission_plugin_manager()
        strategies = plugin_manager.hook.active_submission.get_hookimpls()

        assert {p.function for p in strategies} == {
            pending_job_cancellation_strategy,
            active_job_cancellation_strategy,
            job_metrics_strategy,
            job_data_update_strategy,
        }


class TestActiveSubmissionContext:
    @pytest.fixture(autouse=True, scope="class")
    def mock_info_handler(self):
        with mock.patch("jobbergate_agent.jobbergate.update.InfoHandler", return_value=mock.Mock()) as mock_info_class:
            yield mock_info_class

    @pytest.fixture
    def mock_active_job(self):
        """Fixture providing a mocked ActiveJobSubmission."""
        job = mock.Mock(spec=ActiveJobSubmission)
        job.slurm_job_id = 12345
        job.id = 1
        return job

    def test_slurm_job_id_success(self, mock_active_job):
        """Test slurm_job_id returns the correct ID."""
        context = ActiveSubmissionContext(data=mock_active_job)
        assert context.slurm_job_id == 12345

    def test_slurm_job_id_raises_when_none(self):
        """Test slurm_job_id raises ValueError when ID is None."""
        job = mock.Mock(spec=ActiveJobSubmission)
        job.slurm_job_id = None
        context = ActiveSubmissionContext(data=job)

        with pytest.raises(ValueError, match="Slurm job ID has not been set yet"):
            _ = context.slurm_job_id

    @mock.patch("jobbergate_agent.jobbergate.update.fetch_job_data")
    def test_username(self, mock_fetch, mock_active_job):
        """Test username extraction from slurm_raw_info."""
        mock_fetch.return_value = mock.Mock(job_info='{"user_name": "testuser"}')
        context = ActiveSubmissionContext(data=mock_active_job)

        assert context.username == "testuser"

    def test_username_raises_when_missing(self, mock_active_job):
        """Test username raises ValueError when not in slurm_raw_info."""
        with mock.patch.object(
            ActiveSubmissionContext, "slurm_raw_info", new_callable=mock.PropertyMock, return_value={}
        ):
            context = ActiveSubmissionContext(data=mock_active_job)
            with pytest.raises(ValueError, match="Username could not be fetched"):
                _ = context.username

    @mock.patch("jobbergate_agent.jobbergate.update.fetch_job_data")
    def test_submission_dir(self, mock_fetch, mock_active_job):
        """Test submission_dir extraction from slurm_raw_info."""
        mock_fetch.return_value = mock.Mock(job_info='{"current_working_directory": "/home/testuser/jobs"}')
        context = ActiveSubmissionContext(data=mock_active_job)

        assert context.submission_dir == Path("/home/testuser/jobs")

    @mock.patch("jobbergate_agent.jobbergate.update.InfoHandler")
    def test_info_handler_cached(self, mock_info_class, mock_active_job):
        """Test that info_handler is cached properly."""
        context = ActiveSubmissionContext(data=mock_active_job)

        handler1 = context.info_handler
        handler2 = context.info_handler

        # Should only instantiate once due to cached_property
        assert handler1 is handler2
        assert mock_info_class.call_count == 1
