"""
Provide a ``typer`` app that fetches usage reports from the analytics endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional, cast

import typer
from rich.console import Console
from rich.table import Table

from jobbergate_cli.context import get_active_context
from jobbergate_cli.render import render_json, terminal_message
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import AnalyticsReport, ContextProtocol, SubmissionStatusRow, TemplateUsageRow

app = typer.Typer(
    rich_markup_mode="markdown",
    no_args_is_help=True,
    help="Fetch usage reports aggregated by the Jobbergate API.",
)


class ReportInterval(str, Enum):
    """Supported time buckets for report aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


StartTimeOption = Annotated[
    Optional[datetime],
    typer.Option(
        "--start-time",
        help="Inclusive start of the UTC reporting window. Defaults to one day before the end time.",
    ),
]
EndTimeOption = Annotated[
    Optional[datetime],
    typer.Option(
        "--end-time",
        help="Inclusive end of the UTC reporting window. Defaults to the current time.",
    ),
]
IntervalOption = Annotated[
    Optional[ReportInterval],
    typer.Option(
        "--interval",
        help="Time bucket size for aggregation. Defaults to day.",
    ),
]


def _build_params(
    start_time: Optional[datetime], end_time: Optional[datetime], interval: Optional[ReportInterval]
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if start_time is not None:
        params["start_time"] = start_time.isoformat()
    if end_time is not None:
        params["end_time"] = end_time.isoformat()
    if interval is not None:
        params["interval"] = interval.value
    return params


def _render_report(ctx: ContextProtocol, report: AnalyticsReport[Any], title: str):
    items = [item.model_dump(mode="json") for item in report.items]
    if ctx.raw_output:
        render_json(items)
        return
    if not items:
        terminal_message("No data in the selected window", subject=title)
        return
    table = Table(
        title=title,
        caption=(
            f"{report.start_time:%Y-%m-%d %H:%M} UTC → {report.end_time:%Y-%m-%d %H:%M} UTC, "
            f"interval: {report.interval}, total rows: {len(items)}"
        ),
    )
    for key in items[0].keys():
        table.add_column(key)
    for row in items:
        table.add_row(*[str(value) if value is not None else "" for value in row.values()])
    console = Console()
    console.print()
    console.print(table)
    console.print()


@app.command()
def templates(
    ctx: typer.Context = None,  # type: ignore[assignment]
    start_time: StartTimeOption = None,
    end_time: EndTimeOption = None,
    interval: IntervalOption = None,
):
    """
    Show the number of job submissions per job template, bucketed over time.
    """
    jg_ctx = get_active_context(ctx)
    report = cast(
        AnalyticsReport[TemplateUsageRow],
        make_request(
            jg_ctx.client,
            "/jobbergate/analytics/templates",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve the template usage report from the API",
            support=True,
            response_model_cls=AnalyticsReport[TemplateUsageRow],
            params=_build_params(start_time, end_time, interval),
        ),
    )
    _render_report(jg_ctx, report, "Template usage")


@app.command()
def submissions(
    ctx: typer.Context = None,  # type: ignore[assignment]
    start_time: StartTimeOption = None,
    end_time: EndTimeOption = None,
    interval: IntervalOption = None,
):
    """
    Show the number of job submissions per Jobbergate and Slurm status, bucketed over time.
    """
    jg_ctx = get_active_context(ctx)
    report = cast(
        AnalyticsReport[SubmissionStatusRow],
        make_request(
            jg_ctx.client,
            "/jobbergate/analytics/submissions",
            "GET",
            expected_status=200,
            abort_message="Couldn't retrieve the submission status report from the API",
            support=True,
            response_model_cls=AnalyticsReport[SubmissionStatusRow],
            params=_build_params(start_time, end_time, interval),
        ),
    )
    _render_report(jg_ctx, report, "Submission statuses")
