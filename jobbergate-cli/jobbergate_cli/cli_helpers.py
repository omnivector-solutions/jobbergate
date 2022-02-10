import typing

import snick
from pydantic import BaseModel
from rich import print
from rich.panel import Panel


def terminal_message(message, subject=None):
    panel_kwargs = dict(padding=1)
    if subject is not None:
        panel_kwargs["title"] = f"[green]{subject}"
    print(
        Panel(
            snick.indent(snick.dedent(message), prefix="  "),
            **panel_kwargs,
        )
    )
