"""
Provide command for showing the current environment.
"""

import os
import pathlib

import typer
from loguru import logger

app = typer.Typer()


@app.command()
def show(json: bool = typer.Option(False, help="Dump env as JSON")):
    """
    Print out the current environment settings.
    """
    from jobbergate_api.config import settings

    if json:
        output = json.dumps(settings.dict())
    else:
        output = "\n  ".join(
            ["Jobbergate settings:"] + [
                f"{k}: {v}" for (k, v) in settings.dict().items()
            ],
        )
    print(output)


@app.command()
def link(env_name: str = typer.Argument(..., help="Create sym-link for specified environment")):
    """
    Create the environment link.
    """
    target_path = pathlib.Path(".env")
    if target_path.exists():
        logger.debug("Removing existing env link '.env'")
        target_path.unlink()

    source_path = pathlib.Path(f"{env_name}.env")
    if not target_path.exists():
        typer.echo(f"No environment file {source_path} found for environment {env_name}")
        typer.Exit(1)
    os.symlink(source_path, target_path)
    typer.echo(f"Created link {source_path} -> {target_path}")
