"""
Provide a ``typer`` app that can interact with Cluster data in a cruddy manner.
"""

import typer

from jobbergate_cli.context import get_active_context
from jobbergate_cli.render import terminal_message
from jobbergate_cli.subapps.clusters.tools import get_client_ids

app = typer.Typer(help="Commands to interact with clusters")


@app.command("list")
def list_all(
    ctx: typer.Context = None,  # type: ignore[assignment]
):
    """
    Show available clusters
    """
    jg_ctx = get_active_context(ctx)

    terminal_message("\n".join(get_client_ids(jg_ctx)), subject="Cluster Names", color="yellow", indent=True)
