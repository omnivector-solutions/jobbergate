import typer

from jobbergate_api.cli import dev_server
from jobbergate_api.cli import db_login

app = typer.Typer()
app.command(name="dev-server")(dev_server.dev_server)
app.command(name="db-login")(db_login.db_login)


if __name__ == "__main__":
    app()
