import typing

import typer

from jobbergate_cli.constants import SortOrder
from jobbergate_cli.exceptions import Abort, handle_abort
from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope
from jobbergate_cli.render import StyleMapper, render_list_results, render_single_result, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.subapps.application.tools import fetch_application_data, validate_application_data
from jobbergate_cli.subapps.job_scripts.tools import validate_parameter_file


# move hidden field logic to the API
HIDDEN_FIELDS = [
    "created_at",
    "updated_at",
    "job_script_data_as_string",
]


style_mapper = StyleMapper(
    id = "green",
    job_script_name = "cyan",
)


app = typer.Typer(help="Commands to interact with job scripts")


@app.command()
@handle_abort
def list_all(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all job scripts, even the ones owned by others"),
    search: typing.Optional[str] = typer.Option(None, help="Apply a search term to results"),
    sort_order: SortOrder = typer.Option(SortOrder.UNSORTED, help="Specify sort order"),
    sort_field: typing.Optional[str] = typer.Option(None, help="The field by which results should be sorted"),
):
    """
    Show available job scripts
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None
    assert jg_ctx.client is not None

    params = dict(all=show_all)
    if search is not None:
        params["search"] = search
    if sort_order is not SortOrder.UNSORTED:
        params["sort_ascending"] = SortOrder is SortOrder.ASCENDING
    if sort_field is not None:
        params["sort_field"] = sort_field


    envelope = typing.cast(ListResponseEnvelope, make_request(
        jg_ctx.client,
        "/job-scripts",
        "GET",
        expected_status=200,
        abort_message="Couldn't retrieve job scripts list from API",
        support=True,
        response_model=ListResponseEnvelope,
        params=params,
    ))
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
    id: typing.Optional[int] = typer.Option(
        None,
        help=f"The specific id of the job script.",
    ),
):
    """
    Get a single job script by id
    """
    jg_ctx: JobbergateContext = ctx.obj
    params = dict()

    # Make static type checkers happy
    assert jg_ctx.client is not None

    result = typing.cast(typing.Dict[str, typing.Any], make_request(
        jg_ctx.client,
        f"/job-scripts/{id}",
        "GET",
        expected_status=200,
        abort_message=f"Couldn't retrieve job script {id} from API",
        support=True,
        params=params,
    ))
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
        help=f"The name of the job script to create",
    ),
    application_id: typing.Optional[int] = typer.Option(
        None,
        help=f"The id of the application from which to create the job script",
    ),
    application_identifier: typing.Optional[int] = typer.Option(
        None,
        help=f"The identifier of the application from which to create the job script",
    ),
    sbatch_params: typing.Optional[typing.List[str]] = typer.Option(
        None,
        help="Optional parameter to submit raw sbatch parameters",
    ),
    param_file: typing.Optional[pathlib.Path] = typer.Option(
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
    debug: bool = typer.Option(
        False,
        help="View job script data in the CLI ooutput",
    ),
):
    """
    Create a new job script.
    """
    jg_ctx: JobbergateContext = ctx.obj

    app_data = fetch_application_data(jg_ctx, id=application_id, identifier=application_identifier)
    (app_module, app_config) = validate_application_data(app_data)

    supplied_params = {}
    if param_file:
        supplied_params.update(validate_parameter_file(param_file))
