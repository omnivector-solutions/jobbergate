import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.utils import BadDsn

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import logger


def init_sentry():
    try:
        sentry_logging = LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR)

        sentry_sdk.init(
            dsn=SETTINGS.SENTRY_DSN,
            integrations=[sentry_logging],
            sample_rate=SETTINGS.SENTRY_SAMPLE_RATE,
            profiles_sample_rate=SETTINGS.SENTRY_PROFILING_SAMPLE_RATE,
            traces_sample_rate=SETTINGS.SENTRY_TRACES_SAMPLE_RATE,
            environment=SETTINGS.SENTRY_ENV,
            propagate_traces=False,  # Do not propagate traces to child processes (e.g. sbatch subprocesses)
        )

        logger.debug("##### Enabled Sentry since a valid DSN key was provided.")
    except BadDsn as e:
        logger.debug("##### Sentry could not be enabled: {}".format(e))
