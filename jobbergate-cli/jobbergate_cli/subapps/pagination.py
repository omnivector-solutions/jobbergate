from typing import Any, Dict, List, Optional, cast

import inquirer

from jobbergate_cli.constants import PaginationChoices
from jobbergate_cli.render import StyleMapper, render_paginated_list_results
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, ListResponseEnvelope


def handle_pagination(
    jg_ctx: JobbergateContext,
    url_path: str,
    abort_message: str = "There was an error communicating with the API",
    params: Optional[Dict[str, Any]] = None,
    title: str = "Results List",
    style_mapper: StyleMapper = None,
    hidden_fields: Optional[List[str]] = None,
):
    assert jg_ctx is not None
    assert jg_ctx.client is not None

    current_page = 1

    while True:
        if params is None:
            params = {}
        params["page"] = current_page

        envelope = cast(
            ListResponseEnvelope,
            make_request(
                jg_ctx.client,
                url_path,
                "GET",
                expected_status=200,
                abort_message=abort_message,
                support=True,
                response_model_cls=ListResponseEnvelope,
                params=params,
            ),
        )

        render_paginated_list_results(
            jg_ctx,
            envelope,
            title=title,
            style_mapper=style_mapper,
            hidden_fields=hidden_fields,
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
