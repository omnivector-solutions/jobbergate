"""
Provide a ``typer`` app that can interact with Job Script data in a cruddy manner.
"""

import pathlib
from typing import Any, Dict, List, Optional, cast

import typer

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort, handle_abort
from jobbergate_cli.render import StyleMapper, render_list_results, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope
from jobbergate_cli.subapps.applications.tools import (
    execute_application,
    fetch_application_data,
    validate_application_data,
)
from jobbergate_cli.subapps.job_scripts.tools import fetch_job_script_data, validate_parameter_file
from jobbergate_cli.subapps.job_submissions.app import HIDDEN_FIELDS as JOB_SUBMISSION_HIDDEN_FIELDS
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "created_at",
    "updated_at",
    "job_script_data_as_string",
]


style_mapper = StyleMapper(
    id="green",
    job_script_name="cyan",
)


app = typer.Typer(help="Commands to interact with job scripts")


@app.command()
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
            "/job-scripts",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve job scripts list from API",
            support=True,
            response_model=ListResponseEnvelope,
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
    Get a single job script by id
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
        help="The name of the job script to create",
    ),
    application_id: Optional[int] = typer.Option(
        None,
        help="The id of the application from which to create the job script",
    ),
    application_identifier: Optional[str] = typer.Option(
        None,
        help="The identifier of the application from which to create the job script",
    ),
    sbatch_params: Optional[List[str]] = typer.Option(
        None,
        help="Optional parameter to submit raw sbatch parameters",
    ),
    param_file: Optional[pathlib.Path] = typer.Option(
        None,
        help="""
            Supply a yaml file that contains the parameters for populating templates.
            If this is not supplied, the question asking in the applicaiton is trigered.
        """,
    ),
    fast: bool = typer.Option(
        False,
        help="Use default answers (when available) instead of asking the user.",
    ),
    no_submit: bool = typer.Option(
        False,
        help="Do not ask the user if they want to submit a job",
    ),
):
    """
    Create a new job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    app_data = fetch_application_data(jg_ctx, id=application_id, identifier=application_identifier)
    (app_module, app_config) = validate_application_data(app_data)

    supplied_params = dict(
        job_script_name=name,
        application_id=application_id,
    )
    if param_file:
        supplied_params.update(validate_parameter_file(param_file))

    data = execute_application(
        app_module,
        app_config,
        supplied_params,
        sbatch_params=sbatch_params,
        fast_mode=fast,
    )

    job_script_result = cast(
        Dict[str, Any],
        make_request(
            jg_ctx.client,
            "/job-scripts",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job script",
            support=True,
            json=data,
        ),
    )
    render_single_result(
        jg_ctx,
        job_script_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Script",
    )

    should_submit = True
    if no_submit:
        should_submit = False
    elif not fast:
        should_submit = typer.confirm("Would you like to submit this job immediately?")

    if not should_submit:
        return

    try:
        job_script_id = job_script_result["id"]
        job_script_name = job_script_result["job_script_name"]
        job_submission_result = create_job_submission(jg_ctx, job_script_id, job_script_name)
    except Exception as err:
        raise Abort(
            "Failed to immediately submit the job after job script creation",
            subject="AUTOMATIC JOB SUBMISSION FAILED",
            support=True,
            log_message=f"There was an issue submitting the job immediately {job_script_id=}, {job_script_name=}",
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
    job_script: str = typer.Option(
        ...,
        help="""
            The data with which to update job script.

            Format: string form of dictionary with main script as entry "application.sh"

            Example: '{"application.sh":"#!/bin/bash \\n hostname"}'
        """,
    ),
):
    """
    Update an existing job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None

    job_script_result = cast(
        Dict[str, Any],
        make_request(
            jg_ctx.client,
            f"/job-scripts/{id}",
            "PUT",
            expected_status=202,
            abort_message="Couldn't update job script",
            support=True,
            json=dict(job_script_data_as_string=job_script),
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
        f"/job-scripts/{id}",
        "DELETE",
        expected_status=204,
        abort_message="Request to delete job script was not accepted by the API",
        support=True,
    )
    terminal_message(
        "The job script was successfully deleted.",
        subject="JOB SCRIPT DELETE SUCCEEDED",
    )
