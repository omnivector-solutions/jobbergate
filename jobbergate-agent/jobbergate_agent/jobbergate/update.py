import asyncio
from dataclasses import dataclass
from functools import cached_property, partial
import json
from itertools import chain
import os
from pathlib import Path
import pwd
from subprocess import CompletedProcess
import sys
from textwrap import dedent
from typing import Any, Callable, Coroutine, List, get_args

import msgpack
from jobbergate_core.tools.sbatch import InfoHandler, ScancelHandler, SubprocessHandler
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.clients.influx import influxdb_client
from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT, JobSubmissionStatus
from jobbergate_agent.jobbergate.pagination import fetch_paginated_result
from jobbergate_agent.jobbergate.schemas import (
    ActiveJobSubmission,
    InfluxDBGenericMeasurementDict,
    InfluxDBMeasurementDict,
    InfluxDBPointDict,
    JobSubmissionMetricsMaxResponse,
    SlurmJobData,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.compute import aggregate_influx_measures
from jobbergate_agent.utils.exception import JobbergateAgentError, JobbergateApiError, SbatchError
from jobbergate_agent.utils.logging import log_error
from jobbergate_agent.utils.plugin import get_plugin_manager, hookimpl, hookspec


@dataclass
class SubprocessAsUserHandler(SubprocessHandler):
    """Subprocess handler that runs as a given user."""

    username: str

    def __post_init__(self):
        pwan = pwd.getpwnam(self.username)
        self.uid = pwan.pw_uid
        self.gid = pwan.pw_gid

    def run(self, *args, **kwargs) -> CompletedProcess:
        kwargs.update(user=self.uid, group=self.gid, extra_groups=self.extra_groups, env={})
        # Tests indicate that the change on the working directory precedes the change of user on the subprocess.
        # With that, the user running the agent can face permission denied errors on cwd,
        # depending on the setting on the filesystem and permissions on the directory.
        # To avoid this, we change the working directory after changing to the submitter user using preexec_fn.
        if cwd := kwargs.pop("cwd", None):
            kwargs["preexec_fn"] = lambda: os.chdir(cwd)
        return super().run(*args, **kwargs)

    @cached_property
    def extra_groups(self) -> set[int] | None:
        if not SETTINGS.GET_EXTRA_GROUPS:
            return None
        try:
            result = super().run(cmd=("id", "-G", self.username), capture_output=True, text=True)
        except RuntimeError as e:
            message = f"Failed to get supplementary groups for user {self.username}: {e}"
            logger.error(message)
            raise RuntimeError(message) from e
        return {g for g in map(int, result.stdout.split()) if g != self.gid}


@dataclass
class ActiveSubmissionContext:
    """Context for active job submission processing."""

    data: ActiveJobSubmission

    @property
    def slurm_job_id(self) -> int:
        """The Slurm job ID for the job submission."""
        if self.data.slurm_job_id is None:
            raise ValueError("Slurm job ID has not been set yet")
        return self.data.slurm_job_id

    @cached_property
    def subprocess_handler(self) -> SubprocessAsUserHandler:
        """Subprocess handler for running commands as the submitter user."""
        return SubprocessAsUserHandler(self.username)

    @cached_property
    def info_handler(self) -> InfoHandler:
        """InfoHandler for fetching job info from Slurm."""
        return InfoHandler(scontrol_path=SETTINGS.SCONTROL_PATH)

    @cached_property
    def username(self) -> str:
        """Username of the job submitter."""
        result = self.slurm_raw_info.get("user_name")
        if result is None:
            raise ValueError("Username could not be fetched for the given Slurm job ID")
        return result

    @property
    def submission_dir(self) -> Path:
        """The submission directory for the job submission."""
        result = self.slurm_raw_info.get("current_working_directory")
        if result is None:
            raise ValueError("Submission directory could not be fetched for the given Slurm job ID")
        return Path(result)

    @cached_property
    def slurm_job_data(self) -> SlurmJobData:
        """Fetch the Slurm job data for the job submission."""
        return fetch_job_data(self.slurm_job_id, self.info_handler)

    @cached_property
    def slurm_raw_info(self) -> dict[str, Any]:
        """Fetch the raw Slurm job info for the job submission."""
        if self.slurm_job_data.job_info is None:
            return {}
        return json.loads(self.slurm_job_data.job_info)


JobProcessStrategy = Callable[[], Coroutine[Any, Any, None]]
"""Type alias for job process strategy functions."""


async def empty_strategy() -> None:
    """An empty strategy that does nothing."""
    return None


class ActiveSubmissionPluginSpecs:
    """Hook specifications for active job processing plugins."""

    @hookspec
    def active_submission(self, context: ActiveSubmissionContext) -> JobProcessStrategy:
        return empty_strategy


@hookimpl(specname="active_submission")
def pending_job_cancellation_strategy(context: ActiveSubmissionContext) -> JobProcessStrategy:
    """
    Process the cancellation of a pending job submission.

    I.e., a job submissions that has been marked as cancelled but has no associated slurm job id.
    """

    if context.data.status != JobSubmissionStatus.CANCELLED or context.data.slurm_job_id is not None:
        return empty_strategy

    async def helper() -> None:
        logger.debug(f"Updating job submission {context.data.id} to cancelled state")
        try:
            await update_job_data(
                context.data.id,
                SlurmJobData(
                    job_state="CANCELLED",
                    state_reason="Job was cancelled by the user before a slurm job was created",
                ),
            )
        except Exception as e:
            logger.error(f"API update failed: {e}")

    return helper


@hookimpl(specname="active_submission")
def active_job_cancellation_strategy(context: ActiveSubmissionContext) -> JobProcessStrategy:
    """
    Process the cancellation of an active job submission.

    I.e., a job submission that has been marked as cancelled and has an associated slurm job id.
    """

    if context.data.status != JobSubmissionStatus.CANCELLED or not isinstance(context.data.slurm_job_id, int):
        return empty_strategy

    actual_job_id = context.data.slurm_job_id  # make type checker happy

    async def helper() -> None:
        if actual_job_id is None:
            logger.error(f"Cannot cancel job for job submission {context.data.id}: slurm_job_id is None")
            return

        logger.debug(f"Cancelling job for job submission {context.data.id}")
        scancel_handler = ScancelHandler(scancel_path=SETTINGS.SCANCEL_PATH)
        try:
            scancel_handler.cancel_job(actual_job_id)
        except RuntimeError as e:
            logger.error(f"Failed to cancel slurm job {actual_job_id}: {e}")

    return helper


@hookimpl(specname="active_submission")
def job_metrics_strategy(context: ActiveSubmissionContext) -> JobProcessStrategy:
    """
    Strategy for updating job metrics.
    """

    if not SETTINGS.influx_integration_enabled or context.data.slurm_job_id is None:
        return empty_strategy

    async def helper() -> None:
        logger.debug(f"Updating job metrics for job submission {context.data.id}")
        try:
            await update_job_metrics(context.data)
        except Exception:
            logger.error("Update job metrics failed... skipping for job data update")

    return helper


@hookimpl(specname="active_submission", trylast=True)
def job_data_update_strategy(context: ActiveSubmissionContext) -> JobProcessStrategy:
    """
    Strategy for updating job data.
    """

    if not isinstance(context.data.slurm_job_id, int):
        return empty_strategy
    actual_job_id = context.data.slurm_job_id  # make type checker happy

    async def helper() -> None:
        try:
            slurm_job_data = fetch_job_data(actual_job_id, context.info_handler)
        except Exception as e:
            logger.error(f"Failed to update job data for job submission {context.data.id}: {e}")
            return

        try:
            await update_job_data(context.data.id, slurm_job_data)
        except Exception as e:
            logger.error(f"API update failed: {e}")

    return helper


def fetch_job_data(slurm_job_id: int, info_handler: InfoHandler) -> SlurmJobData:
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
    logger.debug("Fetching active jobs")
    with JobbergateApiError.handle_errors("Failed to fetch active job submissions", do_except=log_error):
        results = await fetch_paginated_result(
            url="/jobbergate/job-submissions/agent/active",
            base_model=ActiveJobSubmission,
        )

    logger.debug(f"Retrieved {len(results)} active job submissions")
    return results


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


def fetch_influx_data(
    job: int,
    measurement: INFLUXDB_MEASUREMENT,
    *,
    time: int | None = None,
    host: str | None = None,
    step: int | None = None,
    task: int | None = None,
) -> list[InfluxDBPointDict]:
    """
    Fetch data from InfluxDB for a given host, step and task.
    """
    with JobbergateAgentError.handle_errors("Failed to fetch measures from InfluxDB", do_except=log_error):
        all_none = all(arg is None for arg in [time, host, step, task])
        all_set = all(arg is not None for arg in [time, host, step, task])

        if not (all_none or all_set):
            raise ValueError("Invalid argument combination: all optional arguments must be either set or None.")

        if all_set:
            query = dedent(f"""
            SELECT * FROM {measurement} WHERE time > $time AND host = $host AND step = $step AND task = $task AND job = $job
            """)
            params = {"time": time, "host": host, "step": str(step), "task": str(task), "job": str(job)}
        else:
            query = f"SELECT * FROM {measurement} WHERE job = $job"
            params = {"job": str(job)}

        assert influxdb_client is not None  # mypy assertion

        logger.debug(f"Querying InfluxDB with: {query=}, {params=}")
        result = influxdb_client.query(query, bind_params=params, epoch="s")
        logger.debug("Successfully fetched data from InfluxDB")

        return [
            InfluxDBPointDict(
                time=point["time"],
                host=point["host"],
                job=point["job"],
                step=point["step"],
                task=point["task"],
                value=point["value"] if point["value"] < 2**63 - 1 else 0,  # prevent int64 overflow
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
        measurements: list[InfluxDBGenericMeasurementDict] = influxdb_client.get_list_measurements()
        logger.debug(f"Fetched measurements from InfluxDB: {measurements=}")
        logger.debug("Filtering compatible measurements")
        return [
            # ignore type since we're filtering the measurements
            InfluxDBMeasurementDict(name=measurement["name"])  # type: ignore[typeddict-item]
            for measurement in measurements
            if measurement["name"] in get_args(INFLUXDB_MEASUREMENT)
        ]


async def update_job_metrics(active_job_submittion: ActiveJobSubmission) -> None:
    """Update job metrics for a job submission.

    This function fetches the metrics from InfluxDB and sends to the API.
    """
    if active_job_submittion.slurm_job_id is None:
        logger.error(f"Cannot update job metrics for job submission {active_job_submittion.id}: slurm_job_id is None")
        return

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

        if not job_max_times.max_times:
            tasks = (
                asyncio.to_thread(
                    fetch_influx_data,
                    active_job_submittion.slurm_job_id,
                    measurement["name"],
                )
                for measurement in influx_measurements
            )
        else:
            tasks = (
                asyncio.to_thread(
                    fetch_influx_data,
                    active_job_submittion.slurm_job_id,
                    measurement["name"],
                    time=int(job_max_time.max_time * 1e9),  # convert to ns since the agent sends in seconds
                    host=job_max_time.node_host,
                    step=job_max_time.step,
                    task=job_max_time.task,
                )
                for job_max_time in job_max_times.max_times
                for measurement in influx_measurements
            )
        results = await asyncio.gather(*list(tasks))
        data_points = chain.from_iterable(results)
        aggregated_data_points = aggregate_influx_measures(data_points)
        if not aggregated_data_points:
            # defer the API call since there's no data to be sent
            return
        packed_data = msgpack.packb(aggregated_data_points)

        response = await jobbergate_api_client.put(
            f"jobbergate/job-submissions/agent/metrics/{active_job_submittion.id}",
            content=packed_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        response.raise_for_status()


active_submission_plugin_manager = partial(
    get_plugin_manager,
    "active_submission",
    hookspec_class=ActiveSubmissionPluginSpecs,
    register=[sys.modules[__name__]],
)


async def update_active_jobs() -> None:
    """
    Update slurm job state for active jobs.
    """
    logger.debug("Started updating slurm job data for active jobs...")

    plugin_manager = active_submission_plugin_manager()
    active_job_submissions = await fetch_active_submissions()
    for active_job in active_job_submissions:
        try:
            for strategy in plugin_manager.hook.active_submission(context=ActiveSubmissionContext(data=active_job)):
                await strategy()
            logger.debug("Finished handling active job_submission {}", active_job.id)
        except Exception as e:
            logger.error("Error processing active job submission {}: {}", active_job.id, e)

    logger.debug("...Finished updating slurm job data for active jobs")
