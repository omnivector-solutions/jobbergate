import typer

from jobbergate_cli.subapps.applications.app import create as create_application
from jobbergate_cli.subapps.applications.app import delete as delete_application
from jobbergate_cli.subapps.applications.app import get_one as get_application
from jobbergate_cli.subapps.applications.app import list_all as list_applications
from jobbergate_cli.subapps.applications.app import update as update_application
from jobbergate_cli.subapps.job_scripts.app import list_all as list_job_scripts


def add_legacy_compatible_commands(app: typer.Typer):

    # Applications
    app.command(
        name="list-applications",
        help="LIST the available applications",
    )(list_applications)
    app.command(
        name="get-application",
        help="GET an Application.",
    )(get_application)
    app.command(
        name="create-application",
        help="CREATE an Application.",
    )(create_application)
    app.command(
        name="delete-application",
        help="DELETE an Application.",
    )(delete_application)
    app.command(
        name="update-application",
        help="UPDATE an Application.",
    )(update_application)

    # Job Scripts
    app.command(
        name="list-job-sripts",
        help="LIST job scripts",
    )(list_job_scripts)
