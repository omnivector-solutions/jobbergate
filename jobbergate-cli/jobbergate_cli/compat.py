import typer

from jobbergate_cli.subapps.applications.app import (
    list_all as list_applications,
    get_one as get_application,
    create as create_application,

)


def add_legacy_compatible_commands(app: typer.Typer):
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
