"""
Provide a stub module to maintain compatibility with previous versions.

Issue a deprecation warning when this module is imported from if JOBBERGATE_COMPATIBILITY_MODE is enabled.

If JOBBERGATE_COMPATIBILITY_MODE is not enabled, raise an import error when this module is imported.
"""

import warnings

from jobbergate_cli.config import settings
from jobbergate_cli.text_tools import dedent, unwrap


if settings.JOBBERGATE_COMPATIBILITY_MODE:

    from jobbergate_cli.subapps.applications.application_helpers import *  # noqa

    warnings.warn(
        dedent(
            """
            Importing jobberappslib from jobbergate_cli is deprecated.
            The module has been moved.
            Import the helper functions from 'jobbergate_cli.subapps.applications.application_helpers' instead",
            """
        ),
        DeprecationWarning,
    )
else:
    raise ImportError(
        unwrap(
            """
            The 'jobberappslib' module has been renamed to 'application_helpers' and has been moved to
            'jobbergate_cli.subapps.applications.application_helpers'
            """
        )
    )
