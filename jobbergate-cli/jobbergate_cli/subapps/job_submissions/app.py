import pathlib
import typing

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


style_mapper = StyleMapper(id="green", job_script_name="cyan", slurm_job_id="orange")


app = typer.Typer(help="Commands to interact with job submissions")


@app.command()
@handle_abort
def create(
    ctx: typer.Context,
    name: str = typer.Option(
        ...,
        help=f"The name of the job submission to create",
    ),
    description: typing.Optional[str] = typer.Option(
        None,
        help="A helpful description of the job submission",
    ),
    job_script_id: int = typer.Option(
        ...,
        help=f"The id of the job_script from which to create the job submission",
    ),
):
    """
    Create a new job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    result = create_job_submission(jg_ctx, job_script_id, name, description=description)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Submission",
    )


@app.command()
@handle_abort
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all job submissions, even the ones owned by others"),
    search: typing.Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.UNSORTED, help="Specify sort order"),
    sort_field: typing.Optional[str] = typer.Option(None, help="The field by which results should be sorted"),
):
    """
    Show available job scripts
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None, "JobbergateContext is uninitialized"
    assert jg_ctx.client is not None, "Client is uninitialized"

    params = dict(all=show_all)
    if search is not None:
        params["search"] = search
    if sort_order is not SortOrder.UNSORTED:
        params["sort_ascending"] = SortOrder is SortOrder.ASCENDING
    if sort_field is not None:
        params["sort_field"] = sort_field

    envelope = typing.cast(
        ListResponseEnvelope,
        make_request(
            jg_ctx.client,
            "/job-submissions",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve job submissions list from API",
            support=True,
            response_model=ListResponseEnvelope,
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
    id: int = typer.Option(int, help=f"The specific id of the job submission."),
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
        help=f"The id of the job submission to delete",
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
        f"/job-submissions/{id}",
        "DELETE",
        expected_status=204,
        abort_message=f"Request to delete job submission was not accepted by the API",
        support=True,
    )
    terminal_message(
        "The job submission was successfully deleted.",
        subject="JOB SUBMISSION DELETE SUCCEEDED",
    )
