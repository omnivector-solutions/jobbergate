"""
Jobbergate command-line interface and app library
"""

import importlib
import warnings

from jobbergate_cli.config import settings


def __getattr__(name: str):
    """
    Overload module attribute lookup to warn if 'appform' is being imported because it is deprecated.
    """
    if name == "appform" and settings.JOBBERGATE_COMPATIBILITY_MODE:
        warnings.warn(
            "appform is deprecated.  Import from 'jobbergate_cli.subapps.applications.questions' instead",
            DeprecationWarning,
        )
        return importlib.import_module("jobbergate_cli.subapps.applications.questions", __name__)

    else:
        raise AttributeError(f"module {__name__} has no attribute {name}")
