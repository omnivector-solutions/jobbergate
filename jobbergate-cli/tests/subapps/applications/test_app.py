from unittest import mock

import httpx
import pytest
from typer.testing import CliRunner

from jobbergate_cli.subapps.applications.app import app
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.exceptions import Abort

DUMMY_DOMAIN = "https://dummy.com"


runner = CliRunner


@pytest.fixture
def dummy_context():
    return JobbergateContext(
        persona=None,
        client=httpx.Client(
            base_url=DUMMY_DOMAIN,
            headers={"Authorization": "Bearer XXXXXXXX"}
        ),
    )


def test_list_all__makes_request_and_renders_results(respx_mock, dummy_context, dummy_data):
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
    with mock.patch("jobbergate_cli.subapps.applications.app.render_list_results"):
        result = runner.invoke(app, ["list-all"])
        assert result.exit_code == 0
