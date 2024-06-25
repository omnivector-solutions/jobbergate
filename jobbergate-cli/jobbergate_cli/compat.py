"""
Provide compatibility to the previous version of Jobbergate CLI for users who have automation or are
familiar with the old commands
"""

import typer

from jobbergate_cli.subapps.applications.app import clone as clone_application
from jobbergate_cli.subapps.applications.app import create as create_application
from jobbergate_cli.subapps.applications.app import delete as delete_application
from jobbergate_cli.subapps.applications.app import download_files as download_files_application
from jobbergate_cli.subapps.applications.app import get_one as get_application
from jobbergate_cli.subapps.applications.app import list_all as list_applications
from jobbergate_cli.subapps.applications.app import update as update_application
from jobbergate_cli.subapps.job_scripts.app import clone as clone_job_script
from jobbergate_cli.subapps.job_scripts.app import create as create_job_script
from jobbergate_cli.subapps.job_scripts.app import create_locally as create_job_script_locally
from jobbergate_cli.subapps.job_scripts.app import delete as delete_job_script
from jobbergate_cli.subapps.job_scripts.app import download_files as download_files_job_script
from jobbergate_cli.subapps.job_scripts.app import get_one as get_job_script
from jobbergate_cli.subapps.job_scripts.app import list_all as list_job_scripts
from jobbergate_cli.subapps.job_scripts.app import show_files as show_files
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
        help="LIST the available applications, replaced by: applications list",
        deprecated=True,
        rich_help_panel="Backward compatibility",
    )(list_applications)
    app.command(
        name="get-application",
        help="GET an Application.",
        deprecated=True,
        hidden=True,
    )(get_application)
    app.command(
        name="create-application",
        help="CREATE an Application.",
        deprecated=True,
        hidden=True,
    )(create_application)
    app.command(
        name="delete-application",
        help="DELETE an Application.",
        deprecated=True,
        hidden=True,
    )(delete_application)
    app.command(
        name="update-application",
        help="UPDATE an Application.",
        deprecated=True,
        hidden=True,
    )(update_application)
    app.command(
        name="download-application",
        help="Download application files.",
        deprecated=True,
        hidden=True,
    )(download_files_application)
    app.command(
        name="clone-application",
        help="Clone an application.",
        deprecated=True,
        hidden=True,
    )(clone_application)

    # Job Scripts
    app.command(
        name="list-job-scripts",
        help="LIST job scripts, replaced by: job-scripts list",
        deprecated=True,
        rich_help_panel="Backward compatibility",
    )(list_job_scripts)
    app.command(
        name="get-job-script",
        help="GET a job script",
        deprecated=True,
        hidden=True,
    )(get_job_script)
    app.command(
        name="create-job-script",
        help="CREATE a job script, replaced by: job-scripts create",
        deprecated=True,
        rich_help_panel="Backward compatibility",
    )(create_job_script)
    app.command(
        name="update-job-script",
        help="UPDATE a job script",
        deprecated=True,
        hidden=True,
    )(update_job_script)
    app.command(
        name="render-job-script-locally",
        help="Render a job script locally, replaced by: job-scripts create-locally",
        deprecated=True,
        hidden=True,
    )(create_job_script_locally)
    app.command(
        name="delete-job-script",
        help="DELETE a job script",
        deprecated=True,
        hidden=True,
    )(delete_job_script)
    app.command(
        name="download-job-script",
        help="Download job script files.",
        deprecated=True,
        hidden=True,
    )(download_files_job_script)
    app.command(
        name="show-job-script-files",
        help="Show job script files.",
        deprecated=True,
        hidden=True,
    )(show_files)
    app.command(
        name="clone-job-script",
        help="Clone a job script.",
        deprecated=True,
        hidden=True,
    )(clone_job_script)

    # Job Submissions
    app.command(
        name="list-job-submissions",
        help="LIST job submissions, replaced by: job-submissions list",
        deprecated=True,
        rich_help_panel="Backward compatibility",
    )(list_job_submissions)
    app.command(
        name="get-job-submission",
        help="GET a job submission",
        deprecated=True,
        hidden=True,
    )(get_job_submission)
    app.command(
        name="create-job-submission",
        help="CREATE a job submission, replaced by: job-submissions create",
        deprecated=True,
        rich_help_panel="Backward compatibility",
    )(create_job_submission)
    app.command(
        name="delete-job-submission",
        help="DELETE a job submission",
        deprecated=True,
        hidden=True,
    )(delete_job_submission)
