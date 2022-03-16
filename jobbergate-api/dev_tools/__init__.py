"""
Provide helper commands for local development.
"""
import typer

from dev_tools import db, dev_server

app = typer.Typer()
app.command(name="dev-server")(dev_server.dev_server)
app.add_typer(db.app, name="db")


if __name__ == "__main__":
    app()
