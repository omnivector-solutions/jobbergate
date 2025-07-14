"""
Describe constants for the job_submissions module.
"""

import enum
from dataclasses import dataclass

from auto_name_enum import AutoNameEnum, auto
from snick import unwrap


class JobSubmissionStatus(AutoNameEnum):
    """
    Defines the set of possible statuses for a Job Submission.
    """

    CREATED = auto()
    SUBMITTED = auto()
    REJECTED = auto()
    DONE = auto()
    ABORTED = auto()
    CANCELLED = auto()


class SlurmJobState(AutoNameEnum):
    """
    Defines the set of possible states for a job submitted to Slurm.
    """

    BOOT_FAIL = auto()
    CANCELLED = auto()
    COMPLETED = auto()
    CONFIGURING = auto()
    COMPLETING = auto()
    DEADLINE = auto()
    FAILED = auto()
    NODE_FAIL = auto()
    OUT_OF_MEMORY = auto()
    PENDING = auto()
    PREEMPTED = auto()
    RUNNING = auto()
    RESV_DEL_HOLD = auto()
    REQUEUE_FED = auto()
    REQUEUE_HOLD = auto()
    REQUEUED = auto()
    RESIZING = auto()
    REVOKED = auto()
    SIGNALING = auto()
    SPECIAL_EXIT = auto()
    STAGE_OUT = auto()
    STOPPED = auto()
    SUSPENDED = auto()
    TIMEOUT = auto()

    # Special job state indicating that something went wrong with SLURM and the job state cannot be recovered
    UNKNOWN = auto()


@dataclass
class SlurmJobStateDetails:
    """
    Defines the details for a given SlurmJobState including abbreviation and description.
    """

    abbreviation: str
    description: str
    is_abort_status: bool = False
    is_done_status: bool = False


slurm_job_state_details = {
    SlurmJobState.BOOT_FAIL: SlurmJobStateDetails(
        abbreviation="BF",
        description=unwrap(
            """
            Job terminated due to launch failure, typically due to a hardware failure
            (e.g. unable to boot the node or block and the job can not be requeued).
            """
        ),
        is_abort_status=True,
    ),
    SlurmJobState.CANCELLED: SlurmJobStateDetails(
        abbreviation="CA",
        description=unwrap(
            """
            Job was explicitly cancelled by the user or system administrator.
            The job may or may not have been initiated.
            """
        ),
        is_abort_status=True,
    ),
    SlurmJobState.COMPLETED: SlurmJobStateDetails(
        abbreviation="CD",
        description="Job has terminated all processes on all nodes with an exit code of zero.",
        is_done_status=True,
    ),
    SlurmJobState.CONFIGURING: SlurmJobStateDetails(
        abbreviation="CF",
        description=unwrap(
            """
            Job has been allocated resources, but are waiting for them to become ready for use
            (e.g. booting).
            """
        ),
    ),
    SlurmJobState.COMPLETING: SlurmJobStateDetails(
        abbreviation="CG",
        description="Job is in the process of completing. Some processes on some nodes may still be active.",
    ),
    SlurmJobState.DEADLINE: SlurmJobStateDetails(
        abbreviation="DL",
        description="Job terminated on deadline.",
        is_abort_status=True,
    ),
    SlurmJobState.FAILED: SlurmJobStateDetails(
        abbreviation="F",
        description="Job terminated with non-zero exit code or other failure condition.",
        is_abort_status=True,
    ),
    SlurmJobState.NODE_FAIL: SlurmJobStateDetails(
        abbreviation="NF",
        description="Job terminated due to failure of one or more allocated nodes.",
        is_abort_status=True,
    ),
    SlurmJobState.OUT_OF_MEMORY: SlurmJobStateDetails(
        abbreviation="OOM",
        description="Job experienced out of memory error.",
    ),
    SlurmJobState.PENDING: SlurmJobStateDetails(
        abbreviation="PD",
        description="Job is awaiting resource allocation.",
    ),
    SlurmJobState.PREEMPTED: SlurmJobStateDetails(
        abbreviation="PR",
        description="Job terminated due to preemption.",
        is_abort_status=True,
    ),
    SlurmJobState.RUNNING: SlurmJobStateDetails(
        abbreviation="R",
        description="Job currently has an allocation.",
    ),
    SlurmJobState.RESV_DEL_HOLD: SlurmJobStateDetails(
        abbreviation="RD",
        description="Job is being held after requested reservation was deleted.",
    ),
    SlurmJobState.REQUEUE_FED: SlurmJobStateDetails(
        abbreviation="RF",
        description="Job is being requeued by a federation.",
    ),
    SlurmJobState.REQUEUE_HOLD: SlurmJobStateDetails(
        abbreviation="RH",
        description="Held job is being requeued.",
    ),
    SlurmJobState.REQUEUED: SlurmJobStateDetails(
        abbreviation="RQ",
        description="Completing job is being requeued.",
    ),
    SlurmJobState.RESIZING: SlurmJobStateDetails(
        abbreviation="RS",
        description="Job is about to change size.",
    ),
    SlurmJobState.REVOKED: SlurmJobStateDetails(
        abbreviation="RV",
        description="Sibling was removed from cluster due to other cluster starting the job.",
    ),
    SlurmJobState.SIGNALING: SlurmJobStateDetails(
        abbreviation="SI",
        description="Job is being signaled.",
    ),
    SlurmJobState.SPECIAL_EXIT: SlurmJobStateDetails(
        abbreviation="SE",
        description=unwrap(
            """
            The job was requeued in a special state.
            This state can be set by users, typically in EpilogSlurmctld,
            if the job has terminated with a particular exit value.
            """
        ),
        is_abort_status=True,
    ),
    SlurmJobState.STAGE_OUT: SlurmJobStateDetails(
        abbreviation="SO",
        description="Job is staging out files.",
    ),
    SlurmJobState.STOPPED: SlurmJobStateDetails(
        abbreviation="ST",
        description=unwrap(
            """
            Job has an allocation, but execution has been stopped with SIGSTOP signal.
            CPUS have been retained by this job.
            """
        ),
    ),
    SlurmJobState.SUSPENDED: SlurmJobStateDetails(
        abbreviation="S",
        description=unwrap(
            """
            Job has an allocation, but execution has been suspended
            and CPUs have been released for other jobs.
            """
        ),
    ),
    SlurmJobState.TIMEOUT: SlurmJobStateDetails(
        abbreviation="TO",
        description="Job terminated upon reaching its time limit.",
        is_abort_status=True,
    ),
    SlurmJobState.UNKNOWN: SlurmJobStateDetails(
        abbreviation="UK",
        description="Indicates that something went wrong with SLURM and the job state cannot be recovered",
        is_abort_status=True,
    ),
}


class JobSubmissionMetricSampleRate(enum.IntEnum):
    """
    Defines the set of possible sample rates for job submission metrics.

    All values are in seconds.
    """

    ten_seconds = 10
    one_minute = 60
    ten_minutes = 600
    one_hour = 3600
    one_week = 604800


class JobSubmissionMetricAggregateNames(AutoNameEnum):
    """
    An enumeration representing different time intervals for aggregating job submission metrics.

    Attributes:
        metrics_nodes_mv_1_week_by_node: Aggregation of metrics by node over a 1-week period.
        metrics_nodes_mv_1_hour_by_node: Aggregation of metrics by node over a 1-hour period.
        metrics_nodes_mv_10_minutes_by_node: Aggregation of metrics by node over a 10-minute period.
        metrics_nodes_mv_1_minute_by_node: Aggregation of metrics by node over a 1-minute period.
        metrics_nodes_mv_10_seconds_by_node: Aggregation of metrics by node over a 10-second period.
        metrics_nodes_mv_1_week_all_nodes: Aggregation of metrics for all nodes over a 1-week period.
        metrics_nodes_mv_1_hour_all_nodes: Aggregation of metrics for all nodes over a 1-hour period.
        metrics_nodes_mv_10_minutes_all_nodes: Aggregation of metrics for all nodes over a 10-minute period.
        metrics_nodes_mv_1_minute_all_nodes: Aggregation of metrics for all nodes over a 1-minute period.
        metrics_nodes_mv_10_seconds_all_nodes: Aggregation of metrics for all nodes over a 10-second period.
    """

    metrics_nodes_mv_1_week_by_node = auto()
    metrics_nodes_mv_1_hour_by_node = auto()
    metrics_nodes_mv_10_minutes_by_node = auto()
    metrics_nodes_mv_1_minute_by_node = auto()
    metrics_nodes_mv_10_seconds_by_node = auto()
    metrics_nodes_mv_1_week_all_nodes = auto()
    metrics_nodes_mv_1_hour_all_nodes = auto()
    metrics_nodes_mv_10_minutes_all_nodes = auto()
    metrics_nodes_mv_1_minute_all_nodes = auto()
    metrics_nodes_mv_10_seconds_all_nodes = auto()
