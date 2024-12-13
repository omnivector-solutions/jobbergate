import asyncio
import json
from itertools import chain
from typing import List

import msgpack
from jobbergate_core.tools.sbatch import InfoHandler
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.clients.influx import influxdb_client
from jobbergate_agent.jobbergate.schemas import (
    ActiveJobSubmission,
    SlurmJobData,
    JobSubmissionMetricsMaxResponse,
    InfluxDBMeasurementDict,
    InfluxDBPointDict,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, SbatchError
from jobbergate_agent.utils.logging import log_error
from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT
from jobbergate_agent.utils.compute import aggregate_influx_measures


async def fetch_job_data(slurm_job_id: int, info_handler: InfoHandler) -> SlurmJobData:
    logger.debug(f"Fetching slurm job status for slurm job {slurm_job_id}")

    try:
        data = info_handler.get_job_info(slurm_job_id)
    except RuntimeError as e:
        logger.error(f"Failed to fetch job state from slurm: {e}")
        return SlurmJobData(
            job_id=slurm_job_id,
            job_state="UNKNOWN",
            job_info="{}",
            state_reason=f"Slurm did not find a job matching id {slurm_job_id}",
        )

    with SbatchError.handle_errors("Failed parse info from slurm", do_except=log_error):
        slurm_state = SlurmJobData.model_validate(data)
        slurm_state.job_info = json.dumps(data)

    return slurm_state


async def fetch_active_submissions() -> List[ActiveJobSubmission]:
    """
    Retrieve a list of active job_submissions.
    """
    with JobbergateApiError.handle_errors("Failed to fetch active job submissions", do_except=log_error):
        response = await jobbergate_api_client.get("jobbergate/job-submissions/agent/active")
        response.raise_for_status()
        active_job_submissions = [ActiveJobSubmission(**ajs) for ajs in response.json().get("items", [])]

    logger.debug(f"Retrieved {len(active_job_submissions)} active job submissions")
    return active_job_submissions


async def update_job_data(
    job_submission_id: int,
    slurm_job_data: SlurmJobData,
) -> None:
    """
    Update a job submission with the job state
    """
    logger.debug(f"Updating {job_submission_id=} with: {slurm_job_data}")

    with JobbergateApiError.handle_errors(
        f"Could not update job data for job submission {job_submission_id} via the API",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.put(
            f"jobbergate/job-submissions/agent/{job_submission_id}",
            json=dict(
                slurm_job_id=slurm_job_data.job_id,
                slurm_job_state=slurm_job_data.job_state,
                slurm_job_info=slurm_job_data.job_info,
                slurm_job_state_reason=slurm_job_data.state_reason,
            ),
        )
        response.raise_for_status()


async def fetch_influx_data(
    time: int, host: str, step: int, task: int, job: int, measurement: INFLUXDB_MEASUREMENT
) -> list[InfluxDBPointDict]:
    """
    Fetch data from InfluxDB for a given host, step and task.
    """
    query = f"""
    SELECT * FROM {measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
    """
    with JobbergateApiError.handle_errors("Failed to fetch data from InfluxDB", do_except=log_error):
        assert influxdb_client is not None  # mypy assertion
        params = dict(time=time, host=host, step=str(step), task=str(task), job=str(job))
        logger.debug(f"Querying InfluxDB with: {query=}, {params=}")
        result = influxdb_client.query(query, bind_params=params, epoch="us")
        logger.debug("Successfully fetched data from InfluxDB")
        return [
            InfluxDBPointDict(
                time=point["time"],
                host=point["host"],
                job=point["job"],
                step=point["step"],
                task=point["task"],
                value=point["value"],
                measurement=measurement,
            )
            for point in result.get_points()
        ]


def fetch_influx_measurements() -> list[InfluxDBMeasurementDict]:
    """
    Fetch measurements from InfluxDB.
    """
    with JobbergateApiError.handle_errors("Failed to fetch measurements from InfluxDB", do_except=log_error):
        logger.debug("Fetching measurements from InfluxDB")
        assert influxdb_client is not None
        measurements: list[InfluxDBMeasurementDict] = influxdb_client.get_list_measurements()
        logger.debug(f"Fetched measurements from InfluxDB: {measurements=}")
        return measurements


async def update_job_metrics(active_job_submittion: ActiveJobSubmission) -> None:
    """Update job metrics for a job submission.

    This function fetches the metrics from InfluxDB and sends to the API.
    """
    with JobbergateApiError.handle_errors(
        f"Could not update job metrics for slurm job {active_job_submittion.slurm_job_id} via the API",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.get(
            f"jobbergate/job-submissions/agent/metrics/{active_job_submittion.id}"
        )
        response.raise_for_status()
        job_max_times = JobSubmissionMetricsMaxResponse(**response.json())

        influx_measurements = fetch_influx_measurements()

        tasks = (
            fetch_influx_data(
                job_max_time.max_time,
                job_max_time.node_host,
                job_max_time.step,
                job_max_time.task,
                active_job_submittion.slurm_job_id,
                measurement["name"],
            )
            for job_max_time in job_max_times.max_times
            for measurement in influx_measurements
        )
        results = await asyncio.gather(*list(tasks))
        data_points = chain.from_iterable(results)
        aggregated_data_points = aggregate_influx_measures(data_points)
        packed_data = msgpack.packb(aggregated_data_points)

        response = await jobbergate_api_client.put(
            f"jobbergate/job-submissions/agent/metrics/{active_job_submittion.id}",
            content=packed_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        response.raise_for_status()


async def update_active_jobs() -> None:
    """
    Update slurm job state for active jobs.
    """
    logger.debug("Started updating slurm job data for active jobs...")

    sbatch_handler = InfoHandler(scontrol_path=SETTINGS.SCONTROL_PATH)

    logger.debug("Fetching active jobs")
    active_job_submissions = await fetch_active_submissions()

    skip = "skipping to next active job"
    for active_job_submission in active_job_submissions:
        if SETTINGS.influx_integration_enabled:
            logger.debug(f"Updating job metrics for job_submission {active_job_submission.id}")
            try:
                await update_job_metrics(active_job_submission)
            except Exception:
                logger.error("Update job metrics failed... skipping for job data update")
                pass

        logger.debug(f"Fetching slurm job state of job_submission {active_job_submission.id}")

        try:
            slurm_job_data: SlurmJobData = await fetch_job_data(active_job_submission.slurm_job_id, sbatch_handler)
        except Exception:
            logger.debug(f"Fetch job data failed...{skip}")
            continue

        try:
            await update_job_data(active_job_submission.id, slurm_job_data)
        except Exception:
            logger.debug(f"API update failed...{skip}")

    logger.debug("...Finished updating slurm job data for active jobs")
