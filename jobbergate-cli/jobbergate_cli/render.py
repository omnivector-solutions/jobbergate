"""
Provide helpers to render output for users.
"""

import json
from typing import Any, Dict, List, Optional

from rich import print, print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import snick

from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope


class StyleMapper:
    """
    Provide a mapper that can set ``rich`` styles for rendered output of data tables and dicts.

    Each subapp configures its own style mapper (based on the columns of its data types) and
    passes it to the ``render*()`` functions below.
    """

    colors: Dict[str, str]

    def __init__(self, **colors: str):
        """
        Initialize the StyleMapper.
        """
        self.colors = colors

    def map_style(self, column: str) -> Dict[str, Any]:
        """
        Map a column name to the style that should be used to render it.
        """
        color = self.colors.get(column, "white")
        return dict(
            style=color,
            header_style=f"bold {color}",
        )


def terminal_message(message, subject=None, color="green", footer=None, indent=True):
    """
    Print a nicely formatted message as output to the user using a ``rich`` ``Panel``.

    :param: message: The message to print out
    :param: subject: An optional subject line to add in the header of the ``Panel``
    :param: color:   An optional color to style the ``subject`` header with
    :param: footer:  An optional message to display in the footer of the ``Panel``
    :param: indent:  Adds padding to the left of the message
    """
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
    style_mapper: Optional[StyleMapper] = None,
    hidden_fields: Optional[List[str]] = None,
    title: str = "Results List",
):
    """
    Render a list of result data items in a ``rich`` ``Table``.

    :param: ctx:           The JobbergateContext. This is needed to detect if ``full`` or ``raw`` output is needed
    :param: envelope:      A ListResponseEnvelope containing the data items
    :param: style_mapper:  The style mapper that should be used to apply styles to the columns of the table
    :param: hidden_fields: Columns that should (if not using ``full`` mode) be hidden in the ``Table`` output
    :param: title:         The title header to include above the ``Table`` output
    """
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
    data: Dict[str, Any],
    title: str = "Data",
    hidden_fields: Optional[List[str]] = None,
):
    """
    Render a dictionary in a ``rich`` ``Table`` That shows the key and value of each item.

    :param: data: The dictionary to render
    :param: title: The title header to include above the ``Table`` output
    :param: hidden_fields: Keys that should be hidden in the ``Table`` output
    """
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
    result: Dict[str, Any],
    hidden_fields: Optional[List[str]] = None,
    title: str = "Result",
):
    """
    Render a single data item in a ``rich`` ``Table.

    :param: ctx:           The JobbergateContext. This is needed to detect if ``full` or ``raw`` output is needed
    :param: result:        The data item to display
    :param: hidden_fields: Rows that should (if not using ``full`` mode) be hidden in the ``Table`` output
    :param: title:         The title header to include above the ``Tale`` output
    """
    if ctx.raw_output:
        print_json(json.dumps(result))
    else:
        if ctx.full_output or hidden_fields is None:
            hidden_fields = []
        render_dict(result, hidden_fields=hidden_fields, title=title)
