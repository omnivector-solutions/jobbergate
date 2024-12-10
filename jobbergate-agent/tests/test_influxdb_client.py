"""Core module for testing the initialization of the InfluxDB client."""

import contextlib
from collections.abc import Callable
from unittest import mock

import pytest

from jobbergate_agent.clients.influx import initialize_influx_client


@mock.patch("jobbergate_agent.clients.influx.InfluxDBClient")
def test_client_is_None_if_integration_is_disabled(
    mocked_InfluxDBClient: mock.MagicMock, tweak_settings: Callable[..., contextlib._GeneratorContextManager]
):
    """Test that the client is None if the Influx integration is disabled."""
    with tweak_settings(INFLUX_DSN=None):
        client = initialize_influx_client()
    mocked_InfluxDBClient.assert_not_called()
    mocked_InfluxDBClient.from_dsn.assert_not_called()
    assert client is None


@pytest.mark.parametrize(
    "pool_size, ssl, verify_ssl, timeout, udp_port, cert",
    [
        (10, True, True, 10, 8089, "/path/to/cert"),
        (20, False, False, 20, 8090, "/path/to/another/cert"),
        (30, True, False, 30, 8091, "/maybe/another/cert"),
    ],
)
@mock.patch("jobbergate_agent.clients.influx.InfluxDBClient")
def test_client_is_initialized(
    mocked_InfluxDBClient: mock.MagicMock,
    pool_size: int,
    ssl: bool,
    verify_ssl: bool,
    timeout: int,
    udp_port: int,
    cert: str,
    tweak_settings: Callable[..., contextlib._GeneratorContextManager],
):
    """Test that the influxdb_client is properly initialized by the function ``initialize_influx_client ``."""
    mocked_InfluxDBClient.from_dsn = mock.Mock(return_value="dummy-value")

    influx_dsn = "influxdb://user:passwd@localhost:8086/database"

    with tweak_settings(
        INFLUX_DSN=influx_dsn,
        INFLUX_POOL_SIZE=pool_size,
        INFLUX_SSL=ssl,
        INFLUX_VERIFY_SSL=verify_ssl,
        INFLUX_TIMEOUT=timeout,
        INFLUX_UDP_PORT=udp_port,
        INFLUX_CERT_PATH=cert,
    ):
        client = initialize_influx_client()

    assert client == "dummy-value"
    mocked_InfluxDBClient.from_dsn.assert_called_once_with(
        influx_dsn,
        pool_size=pool_size,
        ssl=ssl,
        verify_ssl=verify_ssl,
        timeout=timeout,
        udp_port=udp_port,
        cert=cert,
    )
    mocked_InfluxDBClient.assert_not_called()
