import pathlib
import typing

import typer

from jobbergate_cli.exceptions import handle_abort
from jobbergate_cli.render import StyleMapper, render_single_result
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.subapps.job_submissions.tools import create_job_submission


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
    assert jg_ctx.client is not None

    result = create_job_submission(jg_ctx, job_script_id, name, description=description)
    render_single_result(
        jg_ctx,
        result,
        hidden_fields=HIDDEN_FIELDS,
        title="Created Job Submission",
    )
