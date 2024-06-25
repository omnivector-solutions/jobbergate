"""
Provide a ``typer`` app that can interact with Job Script data in a cruddy manner.
"""

import pathlib
import tempfile
from typing import Any, Dict, List, Optional, cast

import typer

from jobbergate_cli.config import settings
from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort, handle_abort
from jobbergate_cli.render import StyleMapper, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobScriptCreateRequest, JobScriptResponse
from jobbergate_cli.subapps.job_scripts.tools import (
    download_job_script_files,
    fetch_job_script_data,
    question_helper,
    render_job_script,
    render_job_script_locally,
    upload_job_script_files,
)
from jobbergate_cli.subapps.job_submissions.app import HIDDEN_FIELDS as JOB_SUBMISSION_HIDDEN_FIELDS
from jobbergate_cli.subapps.job_submissions.tools import job_submissions_factory
from jobbergate_cli.subapps.pagination import handle_pagination
from jobbergate_cli.text_tools import dedent


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "cloned_from_id",
    "created_at",
    "files",
    "is_archived",
    "template",
    "updated_at",
]


style_mapper = StyleMapper(
    job_script_id="green",
    name="cyan",
)


app = typer.Typer(help="Commands to interact with job scripts")


@app.command("list")
@handle_abort
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all job scripts, even the ones owned by others"),
    search: Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.DESCENDING, help="Specify sort order"),
    sort_field: Optional[str] = typer.Option("id", help="The field by which results should be sorted"),
    from_application_id: Optional[int] = typer.Option(
        None,
        help="Filter job-scripts by the application-id they were created from.",
    ),
):
    """
    Show available job scripts
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None
    assert jg_ctx.client is not None

    params: Dict[str, Any] = dict(user_only=not show_all)
    if search is not None:
        params["search"] = search
    if sort_order is not SortOrder.UNSORTED:
        params["sort_ascending"] = sort_order is SortOrder.ASCENDING
    if sort_field is not None:
        params["sort_field"] = sort_field
    if from_application_id is not None:
        params["from_job_script_template_id"] = from_application_id

    handle_pagination(
        jg_ctx=jg_ctx,
        url_path="/jobbergate/job-scripts",
        abort_message="Couldn't retrieve job scripts list from API",
        params=params,
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
        nested_response_model_cls=JobScriptResponse,
    )


@app.command()
@handle_abort
def get_one(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", "-i", help="The specific id of the job script."),
):
    """
    Get a single job script by id.
    """
    jg_ctx: JobbergateContext = ctx.obj
    result = fetch_job_script_data(jg_ctx, id)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Job Script",
    )


@app.command()
@handle_abort
def create_stand_alone(
    ctx: typer.Context,
    name: str = typer.Option(
        ...,
        help=dedent("The name of the job script to create."),
    ),
    description: Optional[str] = typer.Option(
        None,
        help="Optional text describing the job script.",
    ),
    job_script_path: pathlib.Path = typer.Option(..., help="The path to the job script file to upload"),
    supporting_file_path: Optional[List[pathlib.Path]] = typer.Option(
        None,
        help="A path for one of the supporting files to upload",
    ),
):
    """
    Create and upload files for a standalone job script (i.e., unrelated to any application).
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    request_data = JobScriptCreateRequest(
        name=name,
        description=description,
    )

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            "/jobbergate/job-scripts",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job script",
            support=True,
            request_model=request_data,
            response_model_cls=JobScriptResponse,
        ),
    )

    upload_job_script_files(jg_ctx, job_script_result.job_script_id, job_script_path, supporting_file_path)

    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Script",
    )


@app.command()
@handle_abort
def create_locally(
    ctx: typer.Context,
    application_path: pathlib.Path = typer.Argument(
        pathlib.Path("."),
        help="The path to the application directory to use as a template for the job script.",
        dir_okay=True,
    ),
    job_script_name: str = typer.Option(
        "job_script",
        help="The name of the job script to render locally.",
    ),
    output_path: pathlib.Path = typer.Option(
        pathlib.Path("."),
        help="The path to the directory where the rendered job script should be saved.",
        dir_okay=True,
    ),
    sbatch_params: Optional[List[str]] = typer.Option(
        None,
        help="Optional parameter to submit raw sbatch parameters.",
    ),
    param_file: Optional[pathlib.Path] = typer.Option(
        None,
        help=dedent(
            """
            Supply a json file that contains the parameters for populating templates.
            If this is not supplied, the question asking in the application is triggered.
            """
        ),
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Use default answers (when available) instead of asking the user.",
    ),
):
    """
    Create a job-script from local application files (ideal for development and troubleshooting).

    The templates will be overwritten with the rendered files.
    """
    jg_ctx: JobbergateContext = ctx.obj

    render_job_script_locally(
        jg_ctx,
        job_script_name,
        application_path,
        output_path,
        sbatch_params,
        param_file,
        fast,
    )

    terminal_message(
        "The job script was successfully rendered locally.",
        subject="Job script render succeeded",
    )


@app.command()
@handle_abort
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help=dedent(
            """
            The name of the job script to create.
            If this is not supplied, the name will be derived from the base application.
            """
        ),
    ),
    application_id: Optional[int] = typer.Option(
        None,
        "--application-id",
        "-i",
        help="The id of the application from which to create the job script.",
    ),
    application_identifier: Optional[str] = typer.Option(
        None,
        help="The identifier of the application from which to create the job script.",
    ),
    description: Optional[str] = typer.Option(
        None,
        help="Optional text describing the job script.",
    ),
    sbatch_params: Optional[List[str]] = typer.Option(
        None,
        help="Optional parameter to submit raw sbatch parameters.",
    ),
    param_file: Optional[pathlib.Path] = typer.Option(
        None,
        help=dedent(
            """
            Supply a json file that contains the parameters for populating templates.
            If this is not supplied, the question asking in the application is triggered.
            """
        ),
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Use default answers (when available) instead of asking the user.",
    ),
    download: Optional[bool] = typer.Option(
        None,
        help="Download the job script files to the current working directory",
    ),
    submit: Optional[bool] = typer.Option(
        None,
        help="Do not ask the user if they want to submit a job.",
    ),
    cluster_name: Optional[str] = typer.Option(
        None,
        help="The name of the cluster where the job should be submitted to (i.g. 'nash-staging')",
    ),
    execution_directory: Optional[pathlib.Path] = typer.Option(
        None,
        help=dedent(
            """
            The path on the cluster where the job script should be executed.
            If provided as a relative path, it will be converted as an absolute path from your current
            working directory. If you use "~" to denote your home directory, the path will be expanded to an
            absolute path for your home directory on *this* machine.
            """
        ).strip(),
    ),
):
    """
    Create a new job script from an application.
    """
    jg_ctx: JobbergateContext = ctx.obj

    job_script_result = render_job_script(
        jg_ctx,
        name,
        application_id,
        application_identifier,
        description,
        sbatch_params,
        param_file,
        fast,
    )

    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Script",
    )

    # `submit` will be `None` when --submit/--no-submit flag was not set
    if submit is None and (cluster_name or execution_directory):
        # If the user specified --cluster-name or --execution-directory, they must also specify --submit
        raise Abort(
            "You must specify --cluster-name and --execution-directory only on submit mode.",
            subject="Incorrect parameters",
            support=True,
        )

    """
    Invoke `question_helper` to handle the logic for parameters that are not specified by the user.

    If the user specified --fast, the `question_helper` will not invoke the function and will
    instead return the default answer. If the user did not specify --fast, the `question_helper`
    will invoke the function and return the user's answer.
    """

    submit = question_helper(
        question_func=typer.confirm,
        text="Would you like to submit this job immediately?",
        default=True,
        fast=fast,
        actual_value=submit,
    )

    if settings.is_onsite_mode is False or not submit:
        # Notice on-site submission will download the job script files anyway, so it is asked just in remote mode.
        download = question_helper(
            question_func=typer.confirm,
            text="Would you like to download the job script files?",
            default=True,
            fast=fast,
            actual_value=download,
        )

        if download:
            download_job_script_files(job_script_result.job_script_id, jg_ctx, pathlib.Path.cwd())

    if not submit:
        return

    try:
        submissions_handler = job_submissions_factory(
            jg_ctx=jg_ctx,
            job_script_id=job_script_result.job_script_id,
            name=job_script_result.name,
            description=job_script_result.description,
            cluster_name=cluster_name,
            execution_directory=execution_directory,
            sbatch_arguments=None,
        )
        job_submission_result = submissions_handler.run()
    except Exception as err:
        raise Abort(
            "Failed to immediately submit the job after job script creation.",
            subject="Automatic job submission failed",
            support=True,
            log_message="There was an issue submitting the job immediately job_script_id={}".format(
                job_script_result.job_script_id
            ),
            original_error=err,
        )

    render_single_result(
        jg_ctx,
        job_submission_result,
        hidden_fields=JOB_SUBMISSION_HIDDEN_FIELDS,
        title="Created Job Submission (Fast Mode)",
    )


@app.command()
@handle_abort
def update(
    ctx: typer.Context,
    id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="The id of the job script to update",
    ),
    name: Optional[str] = typer.Option(
        None,
        help="Optional new name of the job script.",
    ),
    description: Optional[str] = typer.Option(
        None,
        help="Optional new text describing the job script.",
    ),
):
    """
    Update an existing job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    update_params: Dict[str, Any] = dict()
    if name is not None:
        update_params.update(name=name)
    if description is not None:
        update_params.update(description=description)

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/{id}",
            "PUT",
            expected_status=200,
            abort_message="Couldn't update job script",
            support=True,
            json=update_params,
            response_model_cls=JobScriptResponse,
        ),
    )
    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Updated Job Script",
    )


@app.command()
@handle_abort
def delete(
    ctx: typer.Context,
    id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="The id of the job script to delete",
    ),
):
    """
    Delete an existing job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    make_request(
        jg_ctx.client,
        f"/jobbergate/job-scripts/{id}",
        "DELETE",
        expected_status=204,
        abort_message="Request to delete job script was not accepted by the API",
        support=True,
    )
    terminal_message(
        "The job script was successfully deleted.",
        subject="Job script delete succeeded",
    )


@app.command()
@handle_abort
def show_files(
    ctx: typer.Context,
    id: int = typer.Option(..., help="The specific id of the job script."),
    plain: bool = typer.Option(False, help="Show the files in plain text."),
):
    """
    Show the files for a single job script by id.
    """
    jg_ctx: JobbergateContext = ctx.obj

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        files = download_job_script_files(id, jg_ctx, tmp_path)

        for metadata in files:
            filename = metadata.filename
            file_path = tmp_path / filename
            file_content = file_path.read_text()
            is_main_file = metadata.file_type.upper() == "ENTRYPOINT"
            if plain or jg_ctx.raw_output:
                print()
                print(f"# {filename}")
                if is_main_file:
                    print("# This is the main job script file")
                print(file_content)
            else:
                footer = "This is the main job script file" if is_main_file else None
                terminal_message(file_content, subject=filename, footer=footer)


@app.command()
@handle_abort
def download_files(
    ctx: typer.Context,
    id: int = typer.Option(..., help="The specific id of the job script."),
):
    """
    Download the files from a job script to the current working directory.
    """
    jg_ctx: JobbergateContext = ctx.obj
    downloaded_files = download_job_script_files(id, jg_ctx, pathlib.Path.cwd())

    terminal_message(
        dedent(
            """
            A total of {} job script files were successfully downloaded.
            """.format(len(downloaded_files))
        ),
        subject="Job script download succeeded",
    )


@app.command()
@handle_abort
def clone(
    ctx: typer.Context,
    id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="The id of the job script to update",
    ),
    name: Optional[str] = typer.Option(
        None,
        help="Optional new name of the job script.",
    ),
    description: Optional[str] = typer.Option(
        None,
        help="Optional new text describing the job script.",
    ),
):
    """
    Clone an existing job script, so the user can own and modify a copy of it.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    update_params: Dict[str, Any] = dict()
    if name is not None:
        update_params.update(name=name)
    if description is not None:
        update_params.update(description=description)

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/clone/{id}",
            "POST",
            expected_status=201,
            abort_message="Couldn't clone job script",
            support=True,
            json=update_params,
            response_model_cls=JobScriptResponse,
        ),
    )

    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Cloned Job Script",
    )
