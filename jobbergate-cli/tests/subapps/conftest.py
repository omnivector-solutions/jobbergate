import typing

import httpx
import pytest
from typer import Typer, Context
from typer.testing import CliRunner


from jobbergate_cli.schemas import JobbergateContext


DUMMY_DOMAIN = "https://dummy.com"


cli_runner = CliRunner()


@pytest.fixture
def make_test_app(dummy_context):

    def _main_callback(ctx: Context):
        ctx.obj = dummy_context

    def _helper(command_name: str, command_function: typing.Callable):
        main_app = Typer()
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
