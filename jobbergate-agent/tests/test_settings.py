"""Core module for testing the settings module."""

import pytest

from jobbergate_agent.settings import Settings


def test_settings__manually_set_influx_integration_flag():
    """Test that the InfluxDB integration flag cannot be manually set."""
    with pytest.raises(ValueError):
        Settings(INFLUX_DSN=None, INFLUX_INTEGRATION_ENABLED=True)


@pytest.mark.parametrize(
    "influx_dsn, valid_scheme",
    [
        ("http://localhost:8086", False),
        ("http+influxdb://localhost:8086", False),
        ("ftp://localhost:8086", False),
        ("smtp://localhost:8086", False),
        ("file://localhost:8086", False),
    ],
)
def test_settings__check_invalid_influx_dsn_scheme(influx_dsn: str, valid_scheme: bool):
    """Test if a few invalid DSN schemes raise ValueError."""
    if valid_scheme:
        Settings(INFLUX_DSN=influx_dsn)
    else:
        with pytest.raises(ValueError):
            Settings(INFLUX_DSN=influx_dsn)


def test_settings__check_influx_ssl_cert_path():
    """Test that the SSL certificate path is required when SSL is enabled."""
    with pytest.raises(ValueError):
        Settings(INFLUX_DSN="https+influxdb://localhost:8086", INFLUX_SSL=True, INFLUX_CERT_PATH=None)
