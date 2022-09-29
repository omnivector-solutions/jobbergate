"""
Provide helpers to render output for users.
"""

import json
from typing import Any, Dict, List, Optional, Union, cast

import pydantic
from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope
from jobbergate_cli.text_tools import dedent
from jobbergate_cli.text_tools import indent as indent_text


class StyleMapper:
    """
    Provide a mapper that can set ``rich`` styles for rendered output of data tables and dicts.

    The subapps have list endpoints that return sets of values. These are rendered as tables in
    the output. The StyleMapper class provides a way to simply define styles that should be applied
    to the columns of the table.

    Example:

    The following code will print a table where the columns are colored according to the style_mapper

    .. code-block: python

       style_mapper = StyleMapper(
           a="bold green",
           b="red",
           c="blue",
       )
       envelope = dict(
           results=[
               dict(a=1, b=2, c=3),
               dict(a=4, b=5, c=6),
               dict(a=7, b=8, c=9),
           ],
           pagination=dict(total=3)
       )
       render_list_results(jb_ctx, envelope, style_mapper)

    """

    colors: Dict[str, str]

    def __init__(self, **colors: str):
        """
        Initialize the StyleMapper.
        """
        self.colors = colors

    def map_style(self, column: str) -> Dict[str, Any]:
        """
        Map a column name from the table to display to the style that should be used to render it.
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
    text = dedent(message)
    if indent:
        text = indent_text(text, prefix="  ")
    console = Console()
    console.print()
    console.print(Panel(text, **panel_kwargs))
    console.print()


def render_json(data: Any):
    """
    Print nicely formatted representation of a JSON serializable python primitive.
    """
    console = Console()
    console.print()
    console.print_json(json.dumps(data))
    console.print()


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
    if ctx.raw_output:
        # THIS IS SO DUMB....need to dump to string to make sure paths are converted,
        # then convert back to dict so we can strip out the "results" element, then
        # dump back to string
        serialized = envelope.json()
        deserialized = json.loads(serialized)
        render_json(deserialized["results"])
    else:
        if envelope.pagination.total == 0:
            terminal_message("There are no results to display", subject="Nothing here...")
            return
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

        console = Console()
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
    result: Union[Dict[str, Any], pydantic.BaseModel],
    hidden_fields: Optional[List[str]] = None,
    title: str = "Result",
):
    """
    Render a single data item in a ``rich`` ``Table.

    :param: ctx:           The JobbergateContext. This is needed to detect if ``full` or ``raw`` output is needed
    :param: result:        The data item to display. May be a dict or a pydantic model.
    :param: hidden_fields: Rows that should (if not using ``full`` mode) be hidden in the ``Table`` output
    :param: title:         The title header to include above the ``Tale`` output
    """
    if isinstance(result, pydantic.BaseModel):
        result_model = cast(pydantic.BaseModel, result)
        result_dict = json.loads(result_model.json())
        result = cast(Dict[str, Any], result_dict)

    if ctx.raw_output:
        print_json(json.dumps(result))
    else:
        if ctx.full_output or hidden_fields is None:
            hidden_fields = []
        render_dict(result, hidden_fields=hidden_fields, title=title)
