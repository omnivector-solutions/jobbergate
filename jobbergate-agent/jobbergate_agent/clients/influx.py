"""Core module for defining the InfluxDB client."""

from influxdb import InfluxDBClient
from loguru import logger

from jobbergate_agent.settings import SETTINGS


def initialize_influx_client() -> None | InfluxDBClient:
    """Initialize the InfluxDB client."""
    if SETTINGS.influx_integration_enabled:
        logger.debug("InfluxDB integration is enabled. Initializing InfluxDB client...")
        return InfluxDBClient.from_dsn(
            str(SETTINGS.INFLUX_DSN),
            pool_size=SETTINGS.INFLUX_POOL_SIZE,
            ssl=SETTINGS.INFLUX_SSL,
            verify_ssl=SETTINGS.INFLUX_VERIFY_SSL,
            timeout=SETTINGS.INFLUX_TIMEOUT,
            udp_port=SETTINGS.INFLUX_UDP_PORT,
            cert=SETTINGS.INFLUX_CERT_PATH,
        )
    else:
        logger.debug("InfluxDB integration is disabled")
        return None


influxdb_client = initialize_influx_client()
