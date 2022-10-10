"""
Provide a ``typer`` app that can interact with Job Submission data in a cruddy manner.
"""

from pathlib import Path
from typing import Any, Dict, Optional, cast

import typer

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import handle_abort
from jobbergate_cli.render import StyleMapper, render_list_results, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission, fetch_job_submission_data


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "created_at",
    "updated_at",
]


style_mapper = StyleMapper(id="green", job_script_name="cyan", slurm_job_id="dark_orange")


app = typer.Typer(help="Commands to interact with job submissions")


@app.command()
@handle_abort
def create(
    ctx: typer.Context,
    name: str = typer.Option(
        ...,
        help="The name of the job submission to create",
    ),
    description: Optional[str] = typer.Option(
        None,
        help="A helpful description of the job submission",
    ),
    job_script_id: int = typer.Option(
        ...,
        help="The id of the job_script from which to create the job submission",
    ),
    cluster_name: str = typer.Option(
        None,
        help="The name of the cluster where the job should be submitted (i.g. 'nash-staging')",
    ),
    execution_directory: Optional[Path] = typer.Option(
        None,
        help="""
            The path on the cluster where the job script should be executed.
            If provided as a relative path, it will be converted as an absolute path from your current
            working directory. If you use "~" to denote your home directory, the path will be expanded to an absolute
            path for your home directory on *this* machine.
        """,
    ),
):
    """
    Create a new job submission.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    result = create_job_submission(
        jg_ctx,
        job_script_id,
        name,
        description=description,
        execution_directory=execution_directory,
        cluster_name=cluster_name,
    )
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Submission",
    )


@app.command("list")
@handle_abort
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all job submissions, even the ones owned by others"),
    search: Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.UNSORTED, help="Specify sort order"),
    sort_field: Optional[str] = typer.Option(None, help="The field by which results should be sorted"),
):
    """
    Show available job scripts
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None, "JobbergateContext is uninitialized"
    assert jg_ctx.client is not None, "Client is uninitialized"

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
            "/jobbergate/job-submissions",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve job submissions list from API",
            support=True,
            response_model_cls=ListResponseEnvelope,
            params=params,
        ),
    )
    render_list_results(
        jg_ctx,
        envelope,
        title="Job Submission List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


@app.command()
@handle_abort
def get_one(
    ctx: typer.Context,
    id: int = typer.Option(int, help="The specific id of the job submission."),
):
    """
    Get a single job submission by id
    """
    jg_ctx: JobbergateContext = ctx.obj
    result = fetch_job_submission_data(jg_ctx, id)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Job Submission",
    )


# NOTE: job submissions update is not added because it was an effective noop on the former implementation


@app.command()
@handle_abort
def delete(
    ctx: typer.Context,
    id: int = typer.Option(
        ...,
        help="The id of the job submission to delete",
    ),
):
    """
    Delete an existing job submission.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    make_request(
        jg_ctx.client,
        f"/jobbergate/job-submissions/{id}",
        "DELETE",
        expected_status=204,
        abort_message="Request to delete job submission was not accepted by the API",
        support=True,
    )
    terminal_message(
        "The job submission was successfully deleted.",
        subject="Job submission delete succeeded",
    )
