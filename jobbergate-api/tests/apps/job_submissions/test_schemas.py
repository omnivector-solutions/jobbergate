import math
from typing import Callable
import pytest
import functools

from jobbergate_api.apps.job_submissions.schemas import (
    JobSubmissionCreateRequest,
    JobSubmissionUpdateRequest,
    JobSubmissionMetricSchema,
)
from datetime import datetime


@pytest.mark.parametrize(
    "schema",
    [
        JobSubmissionCreateRequest(name="test", job_script_id=1, execution_directory=""),
        JobSubmissionUpdateRequest(execution_directory=""),
    ],
)
def test_empty_string_to_none(schema):
    """
    Assert that an empty string on execution_directory is converted to None.

    It was causing problems downstream since:
    >>> from pathlib import Path
    >>> Path("")
    PosixPath('.')

    With that, the default value was not applied on the Agent side.
    """
    assert schema.execution_directory is None


class TestJobSubmissionMetricSchema:
    @property
    def isclose(self) -> Callable[[float | int, float | int], bool]:
        """
        Return a function to compare numbers with a tolerance.
        """
        return functools.partial(math.isclose, rel_tol=1e-9, abs_tol=1e-9)

    def test_job_submission_metric_schema_validate_time(self):
        """
        Test that the validate_time method correctly converts datetime to int.
        """
        timestamp = 1638316800
        dt = datetime.fromtimestamp(timestamp)
        schema = JobSubmissionMetricSchema(
            time=dt,
            node_host="node1",
            cpu_frequency=2.5,
            cpu_time=100.0,
            cpu_utilization=50.0,
            gpu_memory=1024,
            gpu_utilization=75.0,
            page_faults=10,
            memory_rss=2048,
            memory_virtual=4096,
            disk_read=500,
            disk_write=300,
        )
        assert schema.time == timestamp

    def test_job_submission_metric_schema_from_iterable(self):
        """
        Test that the from_iterable method correctly creates an instance from an iterable.
        """
        iterable = [
            1638316800,
            "node1",
            None,
            None,
            2.5,
            100.0,
            50.0,
            1024,
            75.0,
            10,
            2048,
            4096,
            500,
            300,
        ]
        schema = JobSubmissionMetricSchema.from_iterable(iterable)
        assert schema.time == 1638316800
        assert schema.node_host == "node1"
        assert self.isclose(schema.cpu_frequency, 2.5)
        assert self.isclose(schema.cpu_time, 100.0)
        assert self.isclose(schema.cpu_utilization, 50.0)
        assert schema.gpu_memory == 1024
        assert self.isclose(schema.gpu_utilization, 75.0)
        assert schema.page_faults == 10
        assert schema.memory_rss == 2048
        assert schema.memory_virtual == 4096
        assert schema.disk_read == 500
        assert schema.disk_write == 300

    def test_job_submission_metric_schema_from_iterable_invalid_length(self):
        """
        Test that the from_iterable method raises a ValueError if the iterable length is incorrect.
        """
        iterable = [
            1638316800,
            "node1",
            2.5,
            100.0,
            50.0,
            1024,
            75.0,
            10,
            2048,
            4096,
            500,
            300,
        ]
        with pytest.raises(ValueError, match="The iterable must have the same length as the model fields."):
            JobSubmissionMetricSchema.from_iterable(iterable)

    def test_job_submission_metric_schema_from_iterable__skip_optional_fields(self):
        """
        Test that the from_iterable method correctly creates an instance from an iterable with optional fields skipped.
        """
        iterable = [
            1638316800,
            "node1",
            2.5,
            100.0,
            50.0,
            1024,
            75.0,
            10,
            2048,
            4096,
            500,
            300,
        ]
        schema = JobSubmissionMetricSchema.from_iterable(iterable, skip_optional=True)
        assert schema.time == 1638316800
        assert schema.step is None
        assert schema.task is None
        assert schema.node_host == "node1"
        assert self.isclose(schema.cpu_frequency, 2.5)
        assert self.isclose(schema.cpu_time, 100.0)
        assert self.isclose(schema.cpu_utilization, 50.0)
        assert schema.gpu_memory == 1024
        assert self.isclose(schema.gpu_utilization, 75.0)
        assert schema.page_faults == 10
        assert schema.memory_rss == 2048
        assert schema.memory_virtual == 4096
        assert schema.disk_read == 500
        assert schema.disk_write == 300
