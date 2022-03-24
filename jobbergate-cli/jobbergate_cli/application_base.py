"""
Provide a stub module to maintain compatibility with previous versions.

Issue a deprecation warning when this module is imported from if JOBBERGATE_COMPATIBILITY_MODE is enabled.

If JOBBERGATE_COMPATIBILITY_MODE is not enabled, raise an import error when this module is imported.
"""

import warnings

from jobbergate_cli.config import settings
from jobbergate_cli.text_tools import dedent, unwrap


if settings.JOBBERGATE_COMPATIBILITY_MODE:

    from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase  # noqa

    warnings.warn(
        dedent(
            """
            Importing application_base from jobbergate_cli is deprecated.
            The module has been moved.
            Import 'application_base' from 'jobbergate_cli.subapps.applications' instead",
            """
        ),
        DeprecationWarning,
    )
else:
    raise ImportError(
        unwrap(
            """
            JobbergateApplicationBase has been moved to
            'jobbergate_cli.subapps.applications.application_base.JobbergateApplicationBase'
            """
        )
    )
