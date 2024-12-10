"""Core module for verifying the constants used in the application."""

from typing import get_args

from jobbergate_agent.jobbergate.constants import INFLUXDB_MEASUREMENT


def test_influxdb_measurement_sorting():
    """Check if the measurements are sorted in ascending order."""
    assert list(get_args(INFLUXDB_MEASUREMENT)) == sorted(get_args(INFLUXDB_MEASUREMENT))
