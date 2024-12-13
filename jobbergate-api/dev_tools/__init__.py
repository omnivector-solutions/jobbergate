"""
Provide helper commands for local development.
"""

import typer

from dev_tools import db, dev_server, show_env, metrics

app = typer.Typer()
app.command(name="dev-server")(dev_server.dev_server)
app.command(name="show-env")(show_env.show_env)
app.command(name="generate-metrics")(metrics.generate_metrics)
app.add_typer(db.app, name="db")


if __name__ == "__main__":
    app()
