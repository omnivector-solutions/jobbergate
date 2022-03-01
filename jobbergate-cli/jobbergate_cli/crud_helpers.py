import json
import typing

import httpx
import pydantic
import snick
from loguru import logger
from rich.console import Console
from rich.table import Table

from jobbergate_cli.cli_helpers import terminal_message
from jobbergate_cli.exceptions import Abort
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

        console.print(table)


def render_single_result(
    ctx: JobbergateContext,
    result: typing.Dict[str, typing.Any],
    hidden_fields: typing.Optional[typing.List[str]] = None,
    title: str = "Result",
):
    console = Console()
    if ctx.raw_output:
        console.print_json(json.dumps(result))
    else:
        if ctx.full_output or hidden_fields is None:
            hidden_fields = []

        table = Table(title=title)
        table.add_column("Key", header_style="bold yellow", style="yellow")
        table.add_column("Value", header_style="bold white", style="white")

        for (key, value) in result.items():
            if key not in hidden_fields:
                table.add_row(key, str(value))

        console.print(table)


ResponseModel = typing.TypeVar('ResponseModel', bound=pydantic.BaseModel)


def make_request(
    client: httpx.Client,
    url_path: str,
    method: str,
    *,
    expected_status: typing.Optional[int] = None,
    abort_message: str = "There was an error communicating with the API",
    abort_subject: str = "REQUEST FAILED",
    support: bool = True,
    response_model: typing.Optional[typing.Type[ResponseModel]] = None,
    **request_kwargs: typing.Any,
) -> typing.Union[ResponseModel, typing.Dict, None]:

    request = client.build_request(method, url_path, **request_kwargs)

    try:
        response = client.send(request)
    except httpx.RequestError as err:
        raise Abort(
            snick.unwrap(
                f"""
                {abort_message}:
                Communication with the API failed.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"There was an error making the request to the API",
            original_error=err,
        )

    if expected_status is not None and response.status_code != expected_status:
        raise Abort(
            snick.unwrap(
                f"""
                {abort_message}
                Received an error response.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"Got an error code for request: {response.status_code}: {response.text}",
        )

    # TODO: constrain methods with a named enum
    if method == "DELETE":
        return

    try:
        data = response.json()
    except Exception as err:
        raise Abort(
            snick.unwrap(
                f"""
                {abort_message}:
                Response carried no data.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"Failed unpacking json: {response.text}",
            original_error=err,
        )
    logger.debug(f"Extracted data from response: {data}")

    if response_model is None:
        return data

    logger.debug("Validating response data with ResponseModel")
    try:
        return response_model(**data)
    except pydantic.ValidationError as err:
        raise Abort(
            snick.unwrap(
                f"""
                {abort_message}:
                Unexpected data in response.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"Unexpeced format in response data: {data}",
            original_error=err,
        )
