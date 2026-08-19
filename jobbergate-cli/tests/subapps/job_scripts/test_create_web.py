import shlex

import httpx
import pytest
import respx

from jobbergate_cli.config import settings
from jobbergate_cli.subapps.job_scripts.app import create_web

DUMMY_CLUSTER_API = "https://cluster-api.dummy.com"


@pytest.fixture
def configured_cluster_api(mocker, dummy_context):
    mocker.patch.object(settings, "CLUSTER_API_URL", DUMMY_CLUSTER_API)
    mocker.patch.object(settings, "CLUSTER_API_PUBLIC_URL", None)
    # the dummy authentication handler is a MagicMock: make the token surface concrete
    dummy_context.authentication_handler.acquire_access.return_value = "Bearer dummy-access-token"
    dummy_context.authentication_handler._refresh_token.is_valid.return_value = False


def test_create_web__aborts_when_cluster_api_is_not_configured(
    make_test_app,
    cli_runner,
    mocker,
):
    mocker.patch.object(settings, "CLUSTER_API_URL", None)
    test_app = make_test_app("create-web", create_web)
    result = cli_runner.invoke(test_app, shlex.split("create-web 1"))
    assert result.exit_code == 1
    assert "Cluster API not configured" in result.stdout


def test_create_web__creates_session_and_shows_terminal_url(
    make_test_app,
    cli_runner,
    configured_cluster_api,
    mocker,
):
    mocked_browser = mocker.patch("jobbergate_cli.auth.open_on_browser", return_value=True)
    test_app = make_test_app("create-web", create_web)

    with respx.mock:
        session_route = respx.post(f"{DUMMY_CLUSTER_API}/jobbergate/sessions").mock(
            return_value=httpx.Response(
                201,
                json={
                    "session_id": "abc123",
                    "status": "PENDING",
                    "application_selector": "1",
                    "slurm_job_id": 13,
                    "url": "/jobbergate/sessions/abc123/terminal/",
                    "otp": "top-secret",
                },
            ),
        )
        poll_route = respx.get(f"{DUMMY_CLUSTER_API}/jobbergate/sessions/abc123").mock(
            return_value=httpx.Response(200, json={"session_id": "abc123", "status": "RUNNING"}),
        )
        result = cli_runner.invoke(test_app, shlex.split("create-web --application-id 1"))

    assert result.exit_code == 0, f"create-web failed: {result.stdout}"
    assert session_route.called
    assert poll_route.called
    # Rich wraps the panel body, so assert the full URL via the browser call instead of stdout
    mocked_browser.assert_called_once_with(
        f"{DUMMY_CLUSTER_API}/jobbergate/sessions/abc123/terminal/?otp=top-secret"
    )


def test_create_web__aborts_when_cluster_api_is_unreachable(
    make_test_app,
    cli_runner,
    configured_cluster_api,
    mocker,
):
    mocker.patch("jobbergate_cli.auth.open_on_browser", return_value=False)
    test_app = make_test_app("create-web", create_web)

    with respx.mock:
        respx.post(f"{DUMMY_CLUSTER_API}/jobbergate/sessions").mock(
            side_effect=httpx.ConnectError("[Errno -2] Name or service not known"),
        )
        result = cli_runner.invoke(test_app, shlex.split("create-web --application-id 1"))

    assert result.exit_code == 1
    assert "Cluster API unavailable" in result.stdout


def test_create_web__aborts_when_session_fails_before_running(
    make_test_app,
    cli_runner,
    configured_cluster_api,
    mocker,
):
    mocker.patch("jobbergate_cli.auth.open_on_browser", return_value=False)
    test_app = make_test_app("create-web", create_web)

    with respx.mock:
        respx.post(f"{DUMMY_CLUSTER_API}/jobbergate/sessions").mock(
            return_value=httpx.Response(
                201,
                json={
                    "session_id": "abc123",
                    "status": "FAILED",
                    "url": "/jobbergate/sessions/abc123/terminal/",
                    "otp": "top-secret",
                },
            ),
        )
        result = cli_runner.invoke(test_app, shlex.split("create-web --application-id 1"))

    assert result.exit_code == 1
    assert "Session failed" in result.stdout
