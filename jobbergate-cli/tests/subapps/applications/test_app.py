import shlex
import typing
from unittest import mock

import httpx
import pytest
import typer
from typer.testing import CliRunner

from jobbergate_cli.subapps.applications.app import (
    list_all,
    get_one,
    style_mapper,
    HIDDEN_FIELDS,
)
from jobbergate_cli.schemas import JobbergateContext, Pagination, ListResponseEnvelope
from jobbergate_cli.exceptions import Abort

DUMMY_DOMAIN = "https://dummy.com"


runner = CliRunner()


@pytest.fixture
def make_test_app(dummy_context):

    def _main_callback(ctx: typer.Context):
        ctx.obj = dummy_context

    def _helper(command_name: str, command_function: typing.Callable):
        main_app = typer.Typer()
        main_app.callback()(_main_callback)
        main_app.command(name=command_name)(command_function)
        return main_app

    return _helper



@pytest.fixture
def dummy_context():
    return JobbergateContext(
        persona=None,
        client=httpx.Client(
            base_url=DUMMY_DOMAIN,
            headers={"Authorization": "Bearer XXXXXXXX"}
        ),
    )


def test_list_all__makes_request_and_renders_results(respx_mock, make_test_app, dummy_context, dummy_data):
    respx_mock.get(f"{DUMMY_DOMAIN}/applications").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_data,
                pagination=dict(
                    total=3,
                )
            )
        ),
    )
    test_app = make_test_app("list-all", list_all)
    with mock.patch("jobbergate_cli.subapps.applications.app.render_list_results") as mocked_render:
        result = runner.invoke(test_app, ["list-all"])
        assert result.exit_code == 0
        mocked_render.assert_called_once_with(
            dummy_context,
            ListResponseEnvelope(
                results=dummy_data,
                pagination=Pagination(total=3),
            ),
            title="Applications List",
            style_mapper=style_mapper,
            hidden_fields=HIDDEN_FIELDS,
        )


def test_get_one__success__using_id(respx_mock, make_test_app, dummy_context, dummy_data):
    respx_mock.get(f"{DUMMY_DOMAIN}/applications/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    with mock.patch("jobbergate_cli.subapps.applications.app.render_single_result") as mocked_render:
        result = runner.invoke(test_app, shlex.split("get-one --id=1"))
        assert result.exit_code == 0
        mocked_render.assert_called_once_with(
            dummy_context,
            dummy_data[0],
            title="Application",
            hidden_fields=HIDDEN_FIELDS,
        )


def test_get_one__success__using_identifier(respx_mock, make_test_app, dummy_context, dummy_data):
    respx_mock.get(f"{DUMMY_DOMAIN}/applications?identifier=dummy").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    with mock.patch("jobbergate_cli.subapps.applications.app.render_single_result") as mocked_render:
        result = runner.invoke(test_app, shlex.split("get-one --identifier=dummy"))
        assert result.exit_code == 0
        mocked_render.assert_called_once_with(
            dummy_context,
            dummy_data[0],
            title="Application",
            hidden_fields=HIDDEN_FIELDS,
        )


def test_get_one__fails_with_neither_id_or_identifier(make_test_app):
    test_app = make_test_app("get-one", get_one)
    result = runner.invoke(test_app, shlex.split("get-one"))
    assert result.exit_code != 0
    assert "You must supply either" in result.stdout


def test_get_one__fails_with_both_id_and_identifier(make_test_app):
    test_app = make_test_app("get-one", get_one)
    result = runner.invoke(test_app, shlex.split("get-one --id=1 --identifier=dummy"))
    assert result.exit_code != 0
    assert "You may not supply both" in result.stdout
