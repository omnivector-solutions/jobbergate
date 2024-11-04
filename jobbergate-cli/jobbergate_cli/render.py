"""
Provide helpers to render output for users.
"""

import json
from typing import Any, Callable, Dict, List, Optional, cast

import pydantic
from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from jobbergate_cli.schemas import ContextProtocol, ListResponseEnvelope
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


def terminal_message(
    message: str, subject: str | None = None, color: str = "green", footer: str | None = None, indent: bool = True
):
    """
    Print a nicely formatted message as output to the user using a ``rich`` ``Panel``.

    Args:
        message: The message to print out.
        subject: An optional subject line to add in the header of the ``Panel``.
        color: An optional color to style the ``subject`` header with. Defaults to "green".
        footer: An optional message to display in the footer of the ``Panel``.
        indent: Adds padding to the left of the message. Defaults to True.
    """
    panel_kwargs: dict[str, Any] = dict(padding=1)
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
    ctx: ContextProtocol,
    envelope: ListResponseEnvelope,
    style_mapper: StyleMapper | None = None,
    hidden_fields: list[str] | None = None,
    title: str = "Results List",
):
    """
    Render a list of result data items in a ``rich`` ``Table``.

    Args:
        ctx: The JobbergateContext. This is needed to detect if ``full`` or ``raw`` output is needed.
        envelope: A ListResponseEnvelope containing the data items.
        style_mapper: The style mapper that should be used to apply styles to the columns of the table.
        hidden_fields: Columns that should (if not using ``full`` mode) be hidden in the ``Table`` output.
        title: The title header to include above the ``Table`` output.
    """
    if ctx.raw_output:
        render_json(envelope.model_dump(mode="json")["items"])
    else:
        if envelope.total == 0:
            terminal_message("There are no results to display", subject="Nothing here...")
            return
        if ctx.full_output or hidden_fields is None:
            filtered_results = envelope.items
        else:
            filtered_results = [{k: v for (k, v) in d.items() if k not in hidden_fields} for d in envelope.items]
        first_row = filtered_results[0]

        table = Table(title=title, caption=f"Total items: {envelope.total}")
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
    data: dict[str, Any],
    title: str = "Data",
    hidden_fields: list[str] | None = None,
):
    """
    Render a dictionary in a ``rich`` ``Table`` that shows the key and value of each item.

    Args:
        data: The dictionary to render.
        title: The title header to include above the ``Table`` output.
        hidden_fields: Keys that should be hidden in the ``Table`` output.
    """
    if hidden_fields is None:
        hidden_fields = []

    table = Table(title=title)
    table.add_column("Key", header_style="bold yellow", style="yellow")
    table.add_column("Value", header_style="bold white", style="white")

    for key, value in data.items():
        if key not in hidden_fields:
            table.add_row(key, str(value))

    console = Console()
    console.print()
    console.print(table)
    console.print()


def render_single_result(
    ctx: ContextProtocol,
    result: dict[str, Any] | pydantic.BaseModel,
    hidden_fields: list[str] | None = None,
    title: str = "Result",
    value_mappers: dict[str, Callable[[Any], Any]] | None = None,
):
    """
    Render a single data item in a ``rich`` ``Table``.

    Args:
        ctx: The JobbergateContext. This is needed to detect if ``full`` or ``raw`` output is needed.
        result: The data item to display. May be a dict or a pydantic model.
        hidden_fields: Rows that should (if not using ``full`` mode) be hidden in the ``Table`` output.
        title: The title header to include above the ``Table`` output.
        value_mappers: Mapping functions to change fields before rendering.
    """
    if isinstance(result, pydantic.BaseModel):
        result_model = cast(pydantic.BaseModel, result)
        result = cast(Dict[str, Any], result_model.model_dump(mode="json"))

    if value_mappers is not None:
        for key, mapper in value_mappers.items():
            result[key] = mapper(result[key])

    if ctx.raw_output:
        print_json(json.dumps(result))
    else:
        if ctx.full_output or hidden_fields is None:
            hidden_fields = []
        render_dict(result, hidden_fields=hidden_fields, title=title)


def render_paginated_list_results(
    ctx: ContextProtocol,
    envelope: ListResponseEnvelope,
    title: str = "Results List",
    style_mapper: Optional[StyleMapper] = None,
    hidden_fields: Optional[List[str]] = None,
    value_mappers: Optional[Dict[str, Callable[[Any], Any]]] = None,
):
    deserialized = envelope.model_dump(mode="json")

    if envelope.total == 0:
        terminal_message("There are no results to display", subject="Nothing here...")
        return

    if ctx.raw_output:
        render_json(deserialized["items"])
        return

    current_page = envelope.page
    total_pages = envelope.pages

    if ctx.full_output or hidden_fields is None:
        filtered_results = deserialized["items"]
    else:
        filtered_results = [{k: v for (k, v) in d.items() if k not in hidden_fields} for d in deserialized["items"]]

    # Apply the value mappers over each key defined in the dict
    mapped_results = filtered_results
    if value_mappers is not None:
        for row in filtered_results:
            for key, mapper in value_mappers.items():
                row[key] = mapper(row[key])

    first_row = mapped_results[0]

    table = Table(
        title=title,
        caption=f"Page: {current_page} of {total_pages} - Items: {len(mapped_results)} of {envelope.total}",
    )
    if style_mapper is None:
        style_mapper = StyleMapper()
    for key in first_row.keys():
        table.add_column(key, **style_mapper.map_style(key))

    for row in mapped_results:
        table.add_row(*[str(v) for v in row.values()])

    console = Console()
    console.print()
    console.print(table)


def render_demo(pre_amble: str | None = None):
    """
    Show the demo for the jobbergate-cli.
    """
    message = dedent(
        """       
        * To create a job-script and run it on the cluster, use the command:

          ```jobbergate job-scripts create --application-identifier <value>```

        * If you need to find your application identifier, run the command:

           ```jobbergate applications list```

           Or search for an application by name:

           ```jobbergate applications list --search <search-term>```

        * For more information on any command run it with the `--help` option.

        * To check all the available commands, refer to:

          ```jobbergate --help```
        """
    )
    console = Console()
    if pre_amble:
        console.print(pre_amble)
    console.print()
    console.print(Panel(Markdown(message), title="Quick Start Guide for Jobbergate-CLI"))
    console.print()
