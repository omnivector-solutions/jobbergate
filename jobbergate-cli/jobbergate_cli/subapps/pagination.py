from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, Union, cast

import inquirer
import pydantic

from jobbergate_cli.constants import PaginationChoices
from jobbergate_cli.render import StyleMapper, render_paginated_list_results
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ContextProtocol, ListResponseEnvelope


def handle_pagination(
    jg_ctx: ContextProtocol,
    url_path: str,
    abort_message: str = "There was an error communicating with the API",
    params: Optional[Dict[str, Any]] = None,
    title: str = "Results List",
    style_mapper: StyleMapper | None = None,
    hidden_fields: List[str] | None = None,
    nested_response_model_cls: Type[pydantic.BaseModel] | None = None,
    value_mappers: Optional[Dict[str, Callable[[Any], Any]]] = None,
):
    current_page = 1

    while True:
        if params is None:
            params = {}
        params["page"] = current_page

        envelope = cast(
            Union[ListResponseEnvelope[Dict[str, Any]], ListResponseEnvelope[pydantic.BaseModel]],
            make_request(
                jg_ctx.client,
                url_path,
                "GET",
                expected_status=200,
                abort_message=abort_message,
                support=True,
                response_model_cls=(
                    ListResponseEnvelope[dict]
                    if nested_response_model_cls is None
                    # mypy doesn't accept dynamic creation of a type in this way
                    # but pydantic requires this to unpack the results correctly
                    else ListResponseEnvelope[nested_response_model_cls]  # type: ignore
                ),
                params=params,
            ),
        )

        render_paginated_list_results(
            jg_ctx,
            envelope,
            title=title,
            style_mapper=style_mapper,
            hidden_fields=hidden_fields,
            value_mappers=value_mappers,
        )

        if envelope.pages <= 1:
            return

        current_page = envelope.page

        message = "Which page would you like to view?"
        choices = [PaginationChoices.PREVIOUS_PAGE, PaginationChoices.NEXT_PAGE, PaginationChoices.EXIT]

        if current_page == 1:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "navigation",
                        message=message,
                        choices=choices[1:],  # remove previous page option
                        default=PaginationChoices.NEXT_PAGE,
                    )
                ]
            )
        elif current_page == envelope.pages:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "navigation",
                        message=message,
                        choices=choices[::2],  # remove next page option
                        default=PaginationChoices.EXIT,
                    )
                ]
            )
        else:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "navigation",
                        message=message,
                        choices=choices,
                        default=PaginationChoices.NEXT_PAGE,
                    )
                ]
            )

        if not answer:
            return

        if answer["navigation"] == PaginationChoices.NEXT_PAGE:
            current_page += 1
        elif answer["navigation"] == PaginationChoices.PREVIOUS_PAGE:
            current_page -= 1
        else:
            return
