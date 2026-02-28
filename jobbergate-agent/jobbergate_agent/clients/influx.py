"""Core module for defining the InfluxDB client."""

from influxdb import InfluxDBClient
from loguru import logger

from jobbergate_agent.settings import SETTINGS


def initialize_influx_client() -> None | InfluxDBClient:
    """Initialize the InfluxDB client."""
    if SETTINGS.influx_integration_enabled:
        logger.debug("InfluxDB integration is enabled. Initializing InfluxDB client...")
        # The verify_ssl parameter maps to requests.Session.verify which accepts:
        #   - True: use system/certifi CA bundle
        #   - False: skip verification
        #   - str path: use as CA bundle file
        # When we have a CA cert path and SSL verification is enabled, pass the
        # cert path as verify_ssl so requests uses it as the CA bundle.
        # NOTE: cert= is for CLIENT certificates (mutual TLS), NOT CA verification.
        # Passing the CA cert as cert= causes OpenSSL "[SSL] PEM lib" error because
        # it tries to load the CA cert as a client cert+key pair.
        if SETTINGS.INFLUX_CERT_PATH and SETTINGS.INFLUX_VERIFY_SSL:
            verify_ssl: bool | str = str(SETTINGS.INFLUX_CERT_PATH)
        else:
            verify_ssl = SETTINGS.INFLUX_VERIFY_SSL
        return InfluxDBClient.from_dsn(
            str(SETTINGS.INFLUX_DSN),
            pool_size=SETTINGS.INFLUX_POOL_SIZE,
            ssl=SETTINGS.INFLUX_SSL,
            verify_ssl=verify_ssl,
            timeout=SETTINGS.INFLUX_TIMEOUT,
            udp_port=SETTINGS.INFLUX_UDP_PORT,
        )
    else:
        logger.debug("InfluxDB integration is disabled")
        return None


influxdb_client = initialize_influx_client()
