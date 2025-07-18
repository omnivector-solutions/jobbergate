"""
Provide a ``typer`` app that can interact with Job Submission data in a cruddy manner.
"""

from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional, cast

import typer

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import StyleMapper, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ContextProtocol, JobSubmissionResponse
from jobbergate_cli.subapps.job_submissions.tools import fetch_job_submission_data, job_submissions_factory
from jobbergate_cli.subapps.pagination import handle_pagination
from jobbergate_cli.subapps.tools import resolve_selection


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "cloned_from_id",
    "created_at",
    "execution_directory",
    "is_archived",
    "job_script",
    "report_message",
    "sbatch_arguments",
    "slurm_job_info",
    "updated_at",
]


style_mapper = StyleMapper(job_submission_id="green", name="cyan", slurm_job_id="dark_orange")


app = typer.Typer(help="Commands to interact with job submissions")


@app.command()
def create(
    ctx: typer.Context,
    job_script_id: Optional[int] = typer.Argument(
        None, help="The id of the job_script from which to create the job submission"
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="The name of the job submission to create",
    ),
    description: Optional[str] = typer.Option(
        None,
        help="A helpful description of the job submission",
    ),
    job_script_id_option: Optional[int] = typer.Option(
        None,
        "--job-script-id",
        "-i",
        help="Alternative way to specify the job script id",
    ),
    cluster_name: str = typer.Option(
        None,
        help="The name of the cluster where the job should be submitted (i.g. 'nash-staging')",
    ),
    execution_directory: Optional[Path] = typer.Option(
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
    sbatch_arguments: Optional[list[str]] = typer.Option(
        None,
        "--sbatch-arguments",
        "-s",
        help=dedent(
            """
            Additional arguments to pass as sbatch directives. These should be provided as a list of strings.
            See more details at: https://slurm.schedmd.com/sbatch.html
            """
        ).strip(),
    ),
    download: bool = typer.Option(
        False,
        help="Download the job script files to the current working directory",
    ),
):
    """
    Create a new job submission.
    """
    jg_ctx: ContextProtocol = ctx.obj
    job_script_id = resolve_selection(job_script_id, job_script_id_option)

    try:
        submissions_handler = job_submissions_factory(
            jg_ctx,
            job_script_id,
            name,
            description=description,
            execution_directory=execution_directory,
            cluster_name=cluster_name,
            sbatch_arguments=sbatch_arguments,
            download=download,
        )
        result = submissions_handler.run()
    except Exception as err:
        raise Abort(
            "Failed to create the job submission",
            subject="Job submission failed",
            support=True,
            log_message=f"There was an issue submitting the job from job_script_id={job_script_id}",
            original_error=err,
        )

    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Submission",
    )


@app.command("list")
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all job submissions, even the ones owned by others",
    ),
    search: Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.DESCENDING, help="Specify sort order"),
    sort_field: Optional[str] = typer.Option("id", help="The field by which results should be sorted"),
    from_job_script_id: Optional[int] = typer.Option(
        None,
        help="Filter job-submissions by the job-script-id they were created from.",
    ),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived entries in the results"),
):
    """
    Show available job submissions.
    """
    jg_ctx: ContextProtocol = ctx.obj

    params: Dict[str, Any] = dict(user_only=not show_all, include_archived=include_archived)
    if search is not None:
        params["search"] = search
    if sort_order is not SortOrder.UNSORTED:
        params["sort_ascending"] = sort_order is SortOrder.ASCENDING
    if sort_field is not None:
        params["sort_field"] = sort_field
    if from_job_script_id is not None:
        params["from_job_script_id"] = from_job_script_id

    value_mappers = None
    organization_id = jg_ctx.authentication_handler.get_identity_data().organization_id
    if organization_id is not None:
        value_mappers = dict(cluster_name=lambda cn: cn.removesuffix(f"-{organization_id}"))

    handle_pagination(
        jg_ctx=jg_ctx,
        url_path="/jobbergate/job-submissions",
        abort_message="Couldn't retrieve job submissions list from API",
        params=params,
        title="Job Submission List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
        nested_response_model_cls=JobSubmissionResponse,
        value_mappers=value_mappers,
    )


@app.command()
def get_one(
    ctx: typer.Context,
    id: Optional[int] = typer.Argument(None, help="The specific id of the job submission to be selected."),
    id_option: Optional[int] = typer.Option(None, "--id", "-i", help="Alternative way to specify id"),
):
    """
    Get a single job submission by id
    """
    jg_ctx: ContextProtocol = ctx.obj
    id = resolve_selection(id, id_option)

    value_mappers = None
    organization_id = jg_ctx.authentication_handler.get_identity_data().organization_id
    if organization_id is not None:
        value_mappers = dict(cluster_name=lambda cn: cn.removesuffix(f"-{organization_id}"))

    result = fetch_job_submission_data(jg_ctx, id)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Job Submission",
        value_mappers=value_mappers,
    )


# NOTE: job submissions update is not added because it was an effective noop on the former implementation


@app.command()
def delete(
    ctx: typer.Context,
    id: Optional[int] = typer.Argument(
        None,
        help="The id of the job submission to delete",
    ),
    id_option: Optional[int] = typer.Option(
        ...,
        "--id",
        "-i",
        help="Alternative way to specify id",
    ),
):
    """
    Delete an existing job submission.
    """
    jg_ctx: ContextProtocol = ctx.obj
    id = resolve_selection(id, id_option)

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


@app.command()
def clone(
    ctx: typer.Context,
    id: Optional[int] = typer.Argument(None, help="The specific id of the job submission to be updated."),
    id_option: Optional[int] = typer.Option(
        None,
        "--id",
        "-i",
        help="Alternative way to specify id.",
    ),
):
    """
    Clone an existing job submission under the CREATED status, so it is re-submitted to the cluster.
    """
    jg_ctx: ContextProtocol = ctx.obj
    id = resolve_selection(id, id_option)

    job_submission_result = cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-submissions/clone/{id}",
            "POST",
            expected_status=201,
            abort_message="Couldn't clone job submission",
            support=True,
            response_model_cls=JobSubmissionResponse,
        ),
    )

    render_single_result(
        jg_ctx,
        job_submission_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Cloned Job Submission",
    )


@app.command()
def cancel(
    ctx: typer.Context,
    id: Optional[int] = typer.Argument(None, help="The specific id of the job submission to be cancelled."),
    id_option: Optional[int] = typer.Option(None, "--id", "-i", help="Alternative way to specify id"),
):
    """
    Cancel an existing job submission.
    """
    jg_ctx: ContextProtocol = ctx.obj
    id = resolve_selection(id, id_option)

    job_submission_result = cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-submissions/cancel/{id}",
            "PUT",
            expected_status=200,
            abort_message="Couldn't cancel job submission",
            support=True,
            response_model_cls=JobSubmissionResponse,
        ),
    )

    render_single_result(
        jg_ctx,
        job_submission_result,
        hidden_fields=HIDDEN_FIELDS,
        title="Cancelled Job Submission",
    )
