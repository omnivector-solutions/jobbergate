import httpx

from jobbergate_cli.constants import PaginationChoices
from jobbergate_cli.schemas import ListResponseEnvelope
from jobbergate_cli.subapps.pagination import handle_pagination


def test_handle_pagination__one_page(respx_mock, dummy_domain, dummy_context, dummy_one_page_results, mocker):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_one_page_results,
        ),
    )

    mock_inquirer = mocker.patch("jobbergate_cli.subapps.pagination.inquirer.prompt")
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    handle_pagination(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-script-templates",
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )

    mock_inquirer.assert_not_called()
    mock_render_paginated.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(**dummy_one_page_results),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )


def test_handle_pagination__show_next_page(respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[0],
        )
    )
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=2").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[1],
        )
    )

    mock_inquirer = mocker.patch("jobbergate_cli.subapps.pagination.inquirer.prompt")
    mock_inquirer.side_effect = [{"navigation": PaginationChoices.NEXT_PAGE}, {"navigation": PaginationChoices.EXIT}]
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    handle_pagination(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-script-templates",
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )

    assert mock_inquirer.call_count == 2
    assert mock_render_paginated.call_count == 2

    assert mock_render_paginated.call_args_list[0] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[0]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )
    assert mock_render_paginated.call_args_list[1] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[1]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )


def test_handle_pagination__show_previous_page(
    respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[0],
        )
    )
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=2").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[1],
        )
    )

    mock_inquirer = mocker.patch("jobbergate_cli.subapps.pagination.inquirer.prompt")
    mock_inquirer.side_effect = [
        {"navigation": PaginationChoices.NEXT_PAGE},
        {"navigation": PaginationChoices.PREVIOUS_PAGE},
        {"navigation": PaginationChoices.EXIT},
    ]
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    handle_pagination(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-script-templates",
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )

    assert mock_inquirer.call_count == 3
    assert mock_render_paginated.call_count == 3

    assert mock_render_paginated.call_args_list[0] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[0]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )
    assert mock_render_paginated.call_args_list[1] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[1]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )
    assert mock_render_paginated.call_args_list[2] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[0]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
    )
