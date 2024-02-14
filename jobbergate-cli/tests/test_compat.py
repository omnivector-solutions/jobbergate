import sys

import pytest
import typer

from jobbergate_cli.compat import add_legacy_compatible_commands


@pytest.fixture
def cleanup_deprecated():
    yield
    for module in list(sys.modules.keys()):
        print("MODULE: ", module)
        if "appform" in module:
            sys.modules.pop(module)
        if "jobberappslib" in module:
            sys.modules.pop(module)
        if "jobbergate_cli.application_base" in module:
            sys.modules.pop(module)


def test_list_all__makes_request_and_renders_results():
    test_app = typer.Typer()
    add_legacy_compatible_commands(test_app)

    registered_command_names = [c.name for c in test_app.registered_commands]

    assert sorted(registered_command_names) == [
        "clone-application",
        "clone-job-script",
        "render-job-script-locally",
        "create-application",
        "create-job-script",
        "create-job-submission",
        "delete-application",
        "delete-job-script",
        "delete-job-submission",
        "download-application",
        "download-job-script",
        "get-application",
        "get-job-script",
        "get-job-submission",
        "list-applications",
        "list-job-scripts",
        "list-job-submissions",
        "show-job-script-files",
        "update-application",
        "update-job-script",
    ]

def test_import_appform_from_jobbergate_cli_warns_and_gives_you_questions_instead_when_in_compatibility_mode(
    tweak_settings, cleanup_deprecated
):
    with tweak_settings(JOBBERGATE_COMPATIBILITY_MODE=True):
        with pytest.warns(DeprecationWarning, match="appform is deprecated"):
            from jobbergate_cli import appform
            from jobbergate_cli.subapps.applications import questions

            assert appform is questions


def test_import_appform_from_jobbergate_cli_raises_an_ImportError_when_not_in_compatibility_mode(cleanup_deprecated):
    with pytest.raises(ImportError):
        from jobbergate_cli import appform  # noqa


def test_import_jobberappslib__from_jobbergate_cli_with_direct_import_of_functions(tweak_settings, cleanup_deprecated):
    with tweak_settings(JOBBERGATE_COMPATIBILITY_MODE=True):
        with pytest.warns(DeprecationWarning, match="Importing jobberappslib from jobbergate_cli is deprecated"):
            from jobbergate_cli.jobberappslib import get_running_jobs as dep_rj
            from jobbergate_cli.subapps.applications.application_helpers import get_running_jobs as new_rj

            assert dep_rj is new_rj


def test_import_jobberappslib_from_jobbergate_cli_raises_ImportError_when_not_in_compatibility_mode(cleanup_deprecated):
    with pytest.raises(ImportError):
        from jobbergate_cli.jobberappslib import get_running_jobs  # noqa


def test_import_application_base_from_jobbergate_cli_warns_and_imports_from_subapp_when_in_compatibility_mode(
    tweak_settings, cleanup_deprecated
):
    with tweak_settings(JOBBERGATE_COMPATIBILITY_MODE=True):
        with pytest.warns(DeprecationWarning, match="application_base from jobbergate_cli is deprecated"):
            from jobbergate_cli.application_base import JobbergateApplicationBase as module_from_base
            from jobbergate_cli.subapps.applications.application_base import (
                JobbergateApplicationBase as module_from_subapp,
            )

            assert module_from_base is module_from_subapp


def test_import_application_base_from_jobbergate_cli_raises_import_error_when_not_in_compatibility_mode(
    cleanup_deprecated,
):
    with pytest.raises(ImportError, match="ApplicationBase has been moved"):
        from jobbergate_cli.application_base import JobbergateApplicationBase  # noqa
