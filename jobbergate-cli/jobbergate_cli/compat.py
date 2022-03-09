"""
Provide compatibility to the previous version of Jobbergate CLI for users who have automation or are
familiar with the old commands
"""

import typer

from jobbergate_cli.subapps.applications.app import create as create_application
from jobbergate_cli.subapps.applications.app import delete as delete_application
from jobbergate_cli.subapps.applications.app import get_one as get_application
from jobbergate_cli.subapps.applications.app import list_all as list_applications
from jobbergate_cli.subapps.applications.app import update as update_application
from jobbergate_cli.subapps.job_scripts.app import create as create_job_script
from jobbergate_cli.subapps.job_scripts.app import delete as delete_job_script
from jobbergate_cli.subapps.job_scripts.app import get_one as get_job_script
from jobbergate_cli.subapps.job_scripts.app import list_all as list_job_scripts
from jobbergate_cli.subapps.job_scripts.app import update as update_job_script
from jobbergate_cli.subapps.job_submissions.app import create as create_job_submission
from jobbergate_cli.subapps.job_submissions.app import delete as delete_job_submission
from jobbergate_cli.subapps.job_submissions.app import get_one as get_job_submission
from jobbergate_cli.subapps.job_submissions.app import list_all as list_job_submissions


def add_legacy_compatible_commands(app: typer.Typer):
    """
    Add commands from the restructured CLI under the previous names for the commands
    to the root ``typer`` app.
    """

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
        name="list-job-scripts",
        help="LIST job scripts",
    )(list_job_scripts)
    app.command(
        name="get-job-script",
        help="GET a job script",
    )(get_job_script)
    app.command(
        name="create-job-script",
        help="CREATE a job script",
    )(create_job_script)
    app.command(
        name="update-job-script",
        help="UPDATE a job script",
    )(update_job_script)
    app.command(
        name="delete-job-script",
        help="DELETE a job script",
    )(delete_job_script)

    # Job Submissions
    app.command(
        name="list-job-submissions",
        help="LIST job submissions",
    )(list_job_submissions)
    app.command(
        name="get-job-submission",
        help="GET a job submission",
    )(get_job_submission)
    app.command(
        name="create-job-submission",
        help="CREATE a job submission",
    )(create_job_submission)
    app.command(
        name="delete-job-submission",
        help="DELETE a job submission",
    )(delete_job_submission)
