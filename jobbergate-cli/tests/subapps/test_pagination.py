import httpx
import pytest

from jobbergate_cli.constants import PaginationChoices
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ListResponseEnvelope
from jobbergate_cli.subapps.pagination import MAX_PAGE_SIZE, handle_pagination


def test_handle_pagination__one_page(respx_mock, dummy_domain, dummy_context, dummy_one_page_results, mocker):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1&size=50").mock(
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
        params={},
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
        value_mappers=None,
    )


def test_handle_pagination__show_next_page(respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1&size=50").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[0],
        )
    )
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=2&size=50").mock(
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
        params={},
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
        value_mappers=None,
    )
    assert mock_render_paginated.call_args_list[1] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[1]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
        value_mappers=None,
    )


def test_handle_pagination__show_previous_page(
    respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=1&size=50").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[0],
        )
    )
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=2&size=50").mock(
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
        params={},
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
        value_mappers=None,
    )
    assert mock_render_paginated.call_args_list[1] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[1]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
        value_mappers=None,
    )
    assert mock_render_paginated.call_args_list[2] == mocker.call(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[0]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
        value_mappers=None,
    )


def test_handle_pagination__non_interactive_page_selection(
    respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=2&size=25").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_two_pages_results[1],
        )
    )

    mock_inquirer = mocker.patch("jobbergate_cli.subapps.pagination.inquirer.prompt")
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    handle_pagination(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-script-templates",
        params={},
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
        page=2,
        size=25,
    )

    mock_inquirer.assert_not_called()
    mock_render_paginated.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(**dummy_two_pages_results[1]),
        title="Applications List",
        style_mapper=None,
        hidden_fields=None,
        value_mappers=None,
    )


def test_handle_pagination__fails_on_out_of_range_page(
    respx_mock, dummy_domain, dummy_context, dummy_two_pages_results, mocker
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates?page=99&size=50").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json={
                **dummy_two_pages_results[1],
                "page": 99,
            },
        )
    )
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    with pytest.raises(Abort, match="Page 99 is out of range"):
        handle_pagination(
            jg_ctx=dummy_context,
            url_path="/jobbergate/job-script-templates",
            params={},
            page=99,
        )

    mock_render_paginated.assert_not_called()


@pytest.mark.parametrize("size", [0, MAX_PAGE_SIZE + 1, -5, None])
def test_handle_pagination__fails_on_out_of_range_size(dummy_context, size, mocker):
    mock_make_request = mocker.patch("jobbergate_cli.subapps.pagination.make_request")
    mock_render_paginated = mocker.patch("jobbergate_cli.subapps.pagination.render_paginated_list_results")

    with pytest.raises(Abort, match="Page size must be between 1 and 100"):
        handle_pagination(
            jg_ctx=dummy_context,
            url_path="/jobbergate/job-script-templates",
            params={},
            size=size,
        )

    mock_make_request.assert_not_called()
    mock_render_paginated.assert_not_called()
