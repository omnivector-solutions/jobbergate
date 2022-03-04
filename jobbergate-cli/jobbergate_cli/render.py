import json
import typing

import snick
from rich import print, print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope


class StyleMapper:
    colors: typing.Dict[str, str]

    def __init__(self, **colors: str):
        self.colors = colors


    def map_style(self, column: str) -> typing.Dict[str, typing.Any]:
        color = self.colors.get(column, "white")
        return dict(
            style=color,
            header_style=f"bold {color}",
        )


def terminal_message(message, subject=None, color="green", footer=None, indent=True):
    panel_kwargs = dict(padding=1)
    if subject is not None:
        panel_kwargs["title"] = f"[{color}]{subject}"
    if footer is not None:
        panel_kwargs["subtitle"] = f"[dim italic]{footer}[/dim italic]"
    text = snick.dedent(message)
    if indent:
        text = snick.indent(text, prefix="  ")
    print(Panel(text, **panel_kwargs))


def render_list_results(
    ctx: JobbergateContext,
    envelope: ListResponseEnvelope,
    style_mapper: typing.Optional[StyleMapper] = None,
    hidden_fields: typing.Optional[typing.List[str]] = None,
    title: str = "Results List",
):
    if envelope.pagination.total == 0:
        terminal_message("There are no results to display", subject="Nothing here...")
        return

    console = Console()
    if ctx.raw_output:
        console.print_json(json.dumps(envelope.results))
    else:
        if ctx.full_output or hidden_fields is None:
            filtered_results = envelope.results
        else:
            filtered_results = [{k: v for (k, v) in d.items() if k not in hidden_fields} for d in envelope.results]
        first_row = filtered_results[0]

        table = Table(title=title, caption=f"Total items: {envelope.pagination.total}")
        if style_mapper is None:
            style_mapper = StyleMapper()
        for key in first_row.keys():
            table.add_column(key, **style_mapper.map_style(key))

        for row in filtered_results:
            table.add_row(*[str(v) for v in row.values()])

        console.print()
        console.print(table)
        console.print()


def render_dict(
    data: typing.Dict[str, typing.Any],
    title: str = "Data",
    hidden_fields: typing.Optional[typing.List[str]] = None,
):
    if hidden_fields is None:
        hidden_fields = []

    table = Table(title=title)
    table.add_column("Key", header_style="bold yellow", style="yellow")
    table.add_column("Value", header_style="bold white", style="white")

    for (key, value) in data.items():
        if key not in hidden_fields:
            table.add_row(key, str(value))

    console = Console()
    console.print()
    console.print(table)
    console.print()


def render_single_result(
    ctx: JobbergateContext,
    result: typing.Dict[str, typing.Any],
    hidden_fields: typing.Optional[typing.List[str]] = None,
    title: str = "Result",
):
    if ctx.raw_output:
        print_json(json.dumps(result))
    else:
        if ctx.full_output or hidden_fields is None:
            hidden_fields = []
        render_dict(result, hidden_fields=hidden_fields, title=title)
