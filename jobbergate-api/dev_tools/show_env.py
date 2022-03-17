"""
Provide command for showing the current environment.
"""

import typer

from jobbergate_api.config import settings

app = typer.Typer()


@app.command()
def show_env(json: bool = typer.Option(False, help="Dump as JSON")):
    """
    Print out the current environment settings.
    """
    if json:
        output = json.dumps(settings.dict())
    else:
        output = "\n  ".join(
            ["Jobbergate settings:"] + [
                f"{k}: {v}" for (k, v) in settings.dict().items()
            ],
        )
    print(output)
