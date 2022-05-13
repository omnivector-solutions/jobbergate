"""
Provide a ``typer`` app that can interact with Cluster data in a cruddy manner.
"""

import typer

from jobbergate_cli.exceptions import handle_abort
from jobbergate_cli.render import terminal_message
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.subapps.clusters.tools import get_cluster_names


app = typer.Typer(help="Commands to interact with clusters")


@app.command("list")
@handle_abort
def list_all(
    ctx: typer.Context,
):
    """
    Show available clusters
    """
    jg_ctx: JobbergateContext = ctx.obj

    # Make static type checkers happy
    assert jg_ctx is not None

    terminal_message("\n".join(get_cluster_names(jg_ctx)), subject="Cluster Names", color="yellow", indent=True)
