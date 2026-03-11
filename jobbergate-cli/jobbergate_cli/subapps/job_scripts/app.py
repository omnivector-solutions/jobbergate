"""
Provide a ``typer`` app that can interact with Job Script data in a cruddy manner.
"""

import pathlib
import tempfile
from typing import Annotated, Any, Dict, List, cast

import typer

from jobbergate_cli.config import settings
from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import StyleMapper, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ContextProtocol, JobScriptCreateRequest, JobScriptResponse
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
from jobbergate_cli.subapps.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, handle_pagination
from jobbergate_cli.subapps.tools import resolve_application_selection, resolve_selection
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

ID_OPTION_HELP = "Alternative way to specify id."


style_mapper = StyleMapper(
    job_script_id="green",
    name="cyan",
)


app = typer.Typer(
    rich_markup_mode="markdown",
    no_args_is_help=True,
    help=dedent(
        """Create and manage job scripts.

        Job scripts contain the instructions for jobs to execute on a Slurm cluster (Python
        files or shell scripts). Once created, job scripts can be submitted to
        affiliated Slurm clusters and monitored through job submissions.

        Workflow: applications → job-scripts → job-submissions

        Quick reference:
        - List your job scripts: `jobbergate job-scripts list`
        - Create one from application: `jobbergate job-scripts create <application id or identifier>`

           **Note:** You are also prompted to *create a job-submission from it right away*.
           This behavior can be controlled by command line arguments.

        - For full guide: `jobbergate --help`
        """
    ),
)


@app.command("list")
def list_all(
    ctx: typer.Context,
    show_all: Annotated[
        bool, typer.Option("--all", help="Show all job scripts, even the ones owned by others")
    ] = False,
    search: Annotated[str | None, typer.Option(help="Apply a search term to results")] = None,
    sort_order: Annotated[SortOrder, typer.Option(help="Specify sort order")] = SortOrder.DESCENDING,
    sort_field: Annotated[str | None, typer.Option(help="The field by which results should be sorted")] = "id",
    from_application_id: Annotated[
        int | None,
        typer.Option(
            help="Filter job-scripts by the application-id they were created from.",
        ),
    ] = None,
    include_archived: Annotated[
        bool, typer.Option("--include-archived", help="Include archived entries in the results")
    ] = False,
    page: Annotated[int | None, typer.Option("--page", "-p", min=1, help="The page number to retrieve")] = None,
    size: Annotated[
        int, typer.Option("--size", "-s", min=1, max=MAX_PAGE_SIZE, help="The number of items per page to retrieve")
    ] = DEFAULT_PAGE_SIZE,
):
    """
    Show available job scripts
    """
    jg_ctx: ContextProtocol = ctx.obj

    params: Dict[str, Any] = {"user_only": not show_all, "include_archived": include_archived}
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
        page=page,
        size=size,
    )


@app.command()
def get_one(
    ctx: typer.Context,
    job_script_id: Annotated[
        int | None, typer.Argument(help="The specific id of the job script to be selected.")
    ] = None,
    job_script_id_option: Annotated[int | None, typer.Option("--id", "-i", help=ID_OPTION_HELP)] = None,
):
    """
    Show a detailed view of a single job script by id.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    result = fetch_job_script_data(jg_ctx, job_script_id)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Job Script",
    )


@app.command()
def create_stand_alone(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Option(
            help=dedent("The name of the job script to create."),
        ),
    ],
    job_script_path: Annotated[
        pathlib.Path | None,
        typer.Argument(help="The path to the job script file to upload", file_okay=True, readable=True),
    ] = None,
    description: Annotated[str | None, typer.Option(help="Optional text describing the job script.")] = None,
    job_script_path_option: Annotated[
        pathlib.Path | None,
        typer.Option(
            "--job-script-path", help="The path to the job script file to upload", file_okay=True, readable=True
        ),
    ] = None,
    supporting_file_path: Annotated[
        List[pathlib.Path] | None,
        typer.Option(
            "--supporting-file",
            "-s",
            help="A path for one of the supporting files to upload",
            file_okay=True,
            readable=True,
        ),
    ] = None,
):
    """
    Create and upload files for a standalone job script (i.e., unrelated to any application).
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_path = resolve_selection(job_script_path, job_script_path_option, option_name="job_script_path")

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
def create_locally(
    ctx: typer.Context,
    application_path: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The path to the application directory to use as a template for the job script.",
            dir_okay=True,
        ),
    ] = pathlib.Path("."),
    job_script_name: Annotated[str, typer.Option(help="The name of the job script to render locally.")] = "job_script",
    output_path: Annotated[
        pathlib.Path,
        typer.Option(
            help="The path to the directory where the rendered job script should be saved.",
            dir_okay=True,
        ),
    ] = pathlib.Path("."),
    sbatch_params: Annotated[
        List[str] | None, typer.Option(help="Optional parameter to submit raw sbatch parameters.")
    ] = None,
    param_file: Annotated[
        pathlib.Path | None,
        typer.Option(
            help=dedent(
                """
                Supply a json file that contains the parameters for populating templates.
                If this is not supplied, the question asking in the application is triggered.
                """
            ),
        ),
    ] = None,
    fast: Annotated[
        bool,
        typer.Option(
            "--fast",
            "-f",
            help="Use default answers (when available) instead of asking the user.",
        ),
    ] = False,
):
    """
    Create a job-script from local application files (ideal for development and troubleshooting).

    The templates will be overwritten with the rendered files.
    """
    jg_ctx: ContextProtocol = ctx.obj

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
def create(
    ctx: typer.Context,
    id_or_identifier: Annotated[
        str | None,
        typer.Argument(
            help="The specific id or identifier of the application from which to create the job script.",
        ),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(
            "--name",
            "-n",
            help=dedent(
                """
                The name of the job script to create.
                If this is not supplied, the name will be derived from the base application.
                """
            ),
        ),
    ] = None,
    application_id: Annotated[
        int | None,
        typer.Option(
            "--application-id",
            "-i",
            help="Alternative way to specify the application id.",
        ),
    ] = None,
    application_identifier: Annotated[
        str | None,
        typer.Option(help="Alternative way to specify the application identifier."),
    ] = None,
    description: Annotated[str | None, typer.Option(help="Optional text describing the job script.")] = None,
    sbatch_params: Annotated[
        List[str] | None,
        typer.Option(help="Optional parameter to submit raw sbatch parameters."),
    ] = None,
    param_file: Annotated[
        pathlib.Path | None,
        typer.Option(
            help=dedent(
                """
                Supply a json file that contains the parameters for populating templates.
                If this is not supplied, the question asking in the application is triggered.
                """
            ),
        ),
    ] = None,
    fast: Annotated[
        bool,
        typer.Option(
            "--fast",
            "-f",
            help="Use default answers (when available) instead of asking the user.",
        ),
    ] = False,
    download: Annotated[
        bool | None,
        typer.Option(help="Download the job script files to the current working directory"),
    ] = None,
    submit: Annotated[
        bool | None,
        typer.Option(help="Do not ask the user if they want to submit a job."),
    ] = None,
    cluster_name: Annotated[
        str | None,
        typer.Option(help="The name of the cluster where the job should be submitted to (i.g. 'nash-staging')"),
    ] = None,
    execution_directory: Annotated[
        pathlib.Path | None,
        typer.Option(
            help=dedent(
                """
                The path on the cluster where the job script should be executed.
                If provided as a relative path, it will be converted as an absolute path from your current
                working directory. If you use "~" to denote your home directory, the path will be expanded to an
                absolute path for your home directory on *this* machine.
                """
            ).strip(),
        ),
    ] = None,
):
    """
    Create a new job script from an application.
    """
    jg_ctx: ContextProtocol = ctx.obj
    selector = resolve_application_selection(id_or_identifier, application_id, application_identifier)

    job_script_result = render_job_script(
        jg_ctx,
        selector,
        name,
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
    except Abort:
        raise
    except Exception as err:
        raise Abort(
            "Failed to immediately submit the job after job script creation.",
            subject="Automatic job submission failed",
            support=True,
            log_message="There was an issue submitting the job immediately job_script_id={}".format(
                job_script_result.job_script_id
            ),
            original_error=err,
        ) from err

    render_single_result(
        jg_ctx,
        job_submission_result,
        hidden_fields=JOB_SUBMISSION_HIDDEN_FIELDS,
        title="Created Job Submission (Fast Mode)",
    )


@app.command()
def update(
    ctx: typer.Context,
    job_script_id: Annotated[int | None, typer.Argument(help="The id of the job script to update")] = None,
    job_script_id_option: Annotated[
        int | None,
        typer.Option(
            "--id",
            "-i",
            help="Alternative way to specify the id of the job script to update",
        ),
    ] = None,
    name: Annotated[str | None, typer.Option(help="Optional new name of the job script.")] = None,
    description: Annotated[str | None, typer.Option(help="Optional new text describing the job script.")] = None,
    is_archived: Annotated[
        bool | None,
        typer.Option("--is-archived", help="Optional value to update is_archived field on this entry"),
    ] = None,
):
    """
    Update an existing job script.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    update_params: dict[str, Any] = {}
    if name is not None:
        update_params.update(name=name)
    if description is not None:
        update_params.update(description=description)
    if is_archived is not None:
        update_params.update(is_archived=is_archived)

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/{job_script_id}",
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
def delete(
    ctx: typer.Context,
    job_script_id: Annotated[int | None, typer.Argument(help="The id of the job script to delete")] = None,
    job_script_id_option: Annotated[
        int | None,
        typer.Option("--id", "-i", help="Alternative way to specify the job script id"),
    ] = None,
):
    """
    Delete an existing job script.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    make_request(
        jg_ctx.client,
        f"/jobbergate/job-scripts/{job_script_id}",
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
def show_files(
    ctx: typer.Context,
    job_script_id: Annotated[int | None, typer.Argument(help="The specific id of the job script to be cloned.")] = None,
    job_script_id_option: Annotated[int | None, typer.Option("--id", "-i", help=ID_OPTION_HELP)] = None,
    plain: Annotated[bool, typer.Option(help="Show the files in plain text.")] = False,
):
    """
    Show the files for a single job script by id.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        files = download_job_script_files(job_script_id, jg_ctx, tmp_path)

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
def download_files(
    ctx: typer.Context,
    job_script_id: Annotated[
        int | None, typer.Argument(help="The specific id of the job script to be downloaded.")
    ] = None,
    job_script_id_option: Annotated[int | None, typer.Option("--id", "-i", help=ID_OPTION_HELP)] = None,
):
    """
    Download the files from a job script to the current working directory.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)
    downloaded_files = download_job_script_files(job_script_id, jg_ctx, pathlib.Path.cwd())

    terminal_message(
        dedent(
            """
            A total of {} job script files were successfully downloaded.
            """.format(len(downloaded_files))
        ),
        subject="Job script download succeeded",
    )


@app.command()
def clone(
    ctx: typer.Context,
    job_script_id: Annotated[
        int | None, typer.Argument(help="The specific id of the job script to be updated.")
    ] = None,
    job_script_id_option: Annotated[
        int | None,
        typer.Option("--id", "-i", help=ID_OPTION_HELP),
    ] = None,
    name: Annotated[str | None, typer.Option(help="Optional new name of the job script.")] = None,
    description: Annotated[str | None, typer.Option(help="Optional new text describing the job script.")] = None,
):
    """
    Clone an existing job script, so the user can own and modify a copy of it.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    update_params: Dict[str, Any] = {}
    if name is not None:
        update_params.update(name=name)
    if description is not None:
        update_params.update(description=description)

    job_script_result = cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/clone/{job_script_id}",
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
