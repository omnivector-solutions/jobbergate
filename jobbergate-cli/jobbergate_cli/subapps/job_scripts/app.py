"""
Provide a ``typer`` app that can interact with Job Script data in a cruddy manner.
"""

import pathlib
from typing import Any, Dict, List, Optional, cast

import typer

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort, handle_abort
from jobbergate_cli.render import StyleMapper, render_json, render_list_results, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import (
    JobbergateContext,
    JobScriptCreateRequestData,
    JobScriptResponse,
    ListResponseEnvelope,
)
from jobbergate_cli.subapps.applications.tools import execute_application, fetch_application_data, load_application_data
from jobbergate_cli.subapps.job_scripts.tools import fetch_job_script_data, validate_parameter_file
from jobbergate_cli.subapps.job_submissions.app import HIDDEN_FIELDS as JOB_SUBMISSION_HIDDEN_FIELDS
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission
from jobbergate_cli.text_tools import dedent


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "created_at",
    "updated_at",
    "job_script_data_as_string",
    "job_script_files",
]


style_mapper = StyleMapper(
    id="green",
    job_script_name="cyan",
)


app = typer.Typer(help="Commands to interact with job scripts")


@app.command("list")
@handle_abort
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all job scripts, even the ones owned by others"),
    search: Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.UNSORTED, help="Specify sort order"),
    sort_field: Optional[str] = typer.Option(None, help="The field by which results should be sorted"),
):
    """
    Show available job scripts
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None
    assert jg_ctx.client is not None

    params: Dict[str, Any] = dict(all=show_all)
    if search is not None:
        params["search"] = search
    if sort_order is not SortOrder.UNSORTED:
        params["sort_ascending"] = SortOrder is SortOrder.ASCENDING
    if sort_field is not None:
        params["sort_field"] = sort_field

    envelope = cast(
        ListResponseEnvelope,
        make_request(
            jg_ctx.client,
            "/jobbergate/job-scripts",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve job scripts list from API",
            support=True,
            response_model_cls=ListResponseEnvelope,
            params=params,
        ),
    )
    render_list_results(
        jg_ctx,
        envelope,
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


@app.command()
@handle_abort
def get_one(
    ctx: typer.Context,
    id: int = typer.Option(int, help="The specific id of the job script."),
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
def create(
    ctx: typer.Context,
    name: str = typer.Option(
        ...,
        help="The name of the job script to create.",
    ),
    application_id: Optional[int] = typer.Option(
        None,
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
        help="Use default answers (when available) instead of asking the user.",
    ),
    submit: Optional[bool] = typer.Option(
        None,
        help="Do not ask the user if they want to submit a job.",
    ),
):
    """
    Create a new job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    app_data = fetch_application_data(jg_ctx, id=application_id, identifier=application_identifier)
    (app_config, app_module) = load_application_data(app_data)

    request_data = JobScriptCreateRequestData(
        application_id=app_data.id,
        job_script_name=name,
        sbatch_params=sbatch_params,
        param_dict=app_config,
        job_script_description=description,
    )

    supplied_params = validate_parameter_file(param_file) if param_file else dict()
    execute_application(app_module, app_config, supplied_params, fast_mode=fast)

    if app_config.jobbergate_config.job_script_name is not None:
        request_data.job_script_name = app_config.jobbergate_config.job_script_name

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
    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Script",
    )

    # `submit` will be `None` --submit/--no-submit flag was not set
    if submit is None:

        # If not running in "fast" mode, ask the user what to do.
        if not fast:
            submit = typer.confirm("Would you like to submit this job immediately?")

        # Otherwise, assume that the job script should be submitted immediately
        else:
            submit = True

    if not submit:
        return

    try:
        job_submission_result = create_job_submission(jg_ctx, job_script_result.id, job_script_result.job_script_name)
    except Exception as err:
        raise Abort(
            "Failed to immediately submit the job after job script creation.",
            subject="Automatic job submission failed",
            support=True,
            log_message=f"There was an issue submitting the job immediately job_script_id={job_script_result.id}.",
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
        help="The id of the job script to update",
    ),
    name: str = typer.Option(
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
        update_params.update(job_script_name=name)
    if description is not None:
        update_params.update(job_script_description=description)

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
    id: int = typer.Option(int, help="The specific id of the job script."),
    plain: bool = typer.Option(False, help="Show the files in plain text."),
):
    """
    Show the files for a single job script by id.
    """
    jg_ctx: JobbergateContext = ctx.obj
    result = fetch_job_script_data(jg_ctx, id)

    if jg_ctx.raw_output:
        render_json(result.job_script_files)
        return

    main_file_path = str(result.job_script_files.main_file_path)

    for (file_path, file_contents) in result.job_script_files.files.items():
        if plain:
            print()
            print(f"# {file_path}")
            if file_path == main_file_path:
                print("# This is the main job script file")
            print(file_contents)
        else:
            footer = "This is the main job script file" if main_file_path == file_path else None
            terminal_message(file_contents, subject=file_path, footer=footer)
