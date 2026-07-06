import re
import threading
from unittest import mock

import click
import pytest
import typer

from jobbergate_cli.auth import show_login_message, track_login_progress
from jobbergate_cli.config import settings
from jobbergate_cli.context import (
    JobbergateContext,
    active_context,
    get_active_context,
    reset_active_context,
    set_active_context,
)
from jobbergate_cli.exceptions import Abort


@mock.patch("jobbergate_cli.context.Client")
def test_client_is_lazy_on_context(mocked_client, tweak_settings):
    ctx = JobbergateContext()

    mocked_client.assert_not_called()

    local_settings = {"BASE_API_URL": "test.example.com/", "JOBBERGATE_REQUESTS_TIMEOUT": 42}

    with tweak_settings(**local_settings):
        client = ctx.client

    assert client == mocked_client.return_value

    mocked_client.assert_called_once_with(
        base_url=local_settings["BASE_API_URL"],
        auth=ctx.authentication_handler,
        timeout=local_settings["JOBBERGATE_REQUESTS_TIMEOUT"],
    )


@mock.patch("jobbergate_cli.context.JobbergateAuthHandler")
def test_authentication_handler_is_lazy_on_context(mocked_auth_handler, tweak_settings):
    ctx = JobbergateContext()

    mocked_auth_handler.assert_not_called()

    local_settings = {
        "OIDC_USE_HTTPS": True,
        "OIDC_DOMAIN": "example.com",
        "OIDC_CLIENT_ID": "client-id",
        "OIDC_CLIENT_SECRET": "client-secret",
    }

    with tweak_settings(**local_settings):
        auth_handler = ctx.authentication_handler

    assert auth_handler == mocked_auth_handler.return_value

    mocked_auth_handler.assert_called_once_with(
        cache_directory=settings.JOBBERGATE_USER_TOKEN_DIR,
        login_domain=f"https://{local_settings['OIDC_DOMAIN']}",
        login_client_id=local_settings["OIDC_CLIENT_ID"],
        login_client_secret=local_settings["OIDC_CLIENT_SECRET"],
        login_url_handler=show_login_message,
        login_sequence_handler=track_login_progress,
    )


@mock.patch("jobbergate_cli.context.JobbergateAuthHandler")
@pytest.mark.parametrize("missing_setting", ["OIDC_DOMAIN", "OIDC_CLIENT_ID"])
def test_authentication_handler__fails_on_missing_setting(mocked_auth_handler, missing_setting, tweak_settings):
    ctx = JobbergateContext()

    local_settings = {
        "OIDC_DOMAIN": "example.com",
        "OIDC_CLIENT_ID": "client-id",
        "OIDC_CLIENT_SECRET": "client-secret",
    }

    local_settings[missing_setting] = None

    with tweak_settings(**local_settings):
        with pytest.raises(
            Abort,
            match=re.compile(
                f"The following settings are required to enable authenticated requests:.*{missing_setting}$",
                flags=re.DOTALL,
            ),
        ):
            _ = ctx.authentication_handler

    mocked_auth_handler.assert_not_called()


class TestActiveContext:
    """
    Test the ContextVar based active context mechanism.
    """

    def test_get_active_context__raises_abort_when_no_context_is_available(self):
        with pytest.raises(Abort, match="No active Jobbergate context"):
            get_active_context()

    def test_get_active_context__returns_the_override_when_provided(self):
        override = mock.Mock()
        assert get_active_context(override) is override

    def test_get_active_context__returns_the_context_var_value(self):
        context = mock.Mock()
        token = set_active_context(context)
        try:
            assert get_active_context() is context
        finally:
            reset_active_context(token)

    def test_get_active_context__override_takes_precedence_over_context_var(self):
        context = mock.Mock()
        override = mock.Mock()
        token = set_active_context(context)
        try:
            assert get_active_context(override) is override
        finally:
            reset_active_context(token)

    @pytest.mark.parametrize("context_class", [click.Context, typer.Context])
    def test_get_active_context__unwraps_a_click_context_override(self, context_class):
        context = mock.Mock()
        click_ctx = mock.Mock(spec=context_class)
        click_ctx.obj = context
        assert get_active_context(click_ctx) is context

    @pytest.mark.parametrize("context_class", [click.Context, typer.Context])
    def test_get_active_context__falls_back_to_context_var_when_click_context_has_no_obj(self, context_class):
        context = mock.Mock()
        click_ctx = mock.Mock(spec=context_class)
        click_ctx.obj = None
        with active_context(context):
            assert get_active_context(click_ctx) is context

    def test_get_active_context__rejects_an_override_that_is_not_a_context(self):
        """
        Guard the trap of calling a command with a positional value that binds to the ``ctx`` parameter.
        """
        with pytest.raises(Abort, match="keyword arguments"):
            get_active_context("my-app")  # type: ignore[arg-type]

    def test_set_and_reset_active_context__round_trip(self):
        first = mock.Mock()
        second = mock.Mock()

        first_token = set_active_context(first)
        second_token = set_active_context(second)
        assert get_active_context() is second

        reset_active_context(second_token)
        assert get_active_context() is first

        reset_active_context(first_token)
        with pytest.raises(Abort, match="No active Jobbergate context"):
            get_active_context()

    def test_active_context__sets_and_restores_the_previous_value(self):
        outer = mock.Mock()
        inner = mock.Mock()
        with active_context(outer) as outer_context:
            assert outer_context is outer
            assert get_active_context() is outer
            with active_context(inner):
                assert get_active_context() is inner
            assert get_active_context() is outer
        with pytest.raises(Abort, match="No active Jobbergate context"):
            get_active_context()

    def test_active_context__restores_the_previous_value_on_exception(self):
        context = mock.Mock()
        with pytest.raises(RuntimeError, match="boom"):
            with active_context(context):
                assert get_active_context() is context
                raise RuntimeError("boom")
        with pytest.raises(Abort, match="No active Jobbergate context"):
            get_active_context()

    def test_active_context__does_not_propagate_to_a_new_thread(self):
        context = mock.Mock()
        thread_results = {}

        def probe():
            try:
                thread_results["context"] = get_active_context()
            except Abort as err:
                thread_results["error"] = err

        with active_context(context):
            thread = threading.Thread(target=probe)
            thread.start()
            thread.join()

        assert "context" not in thread_results
        assert isinstance(thread_results["error"], Abort)


def test_main_callback__sets_the_active_context():
    """
    Verify that invoking the real app through the ``main()`` callback sets the active context.
    """
    from typer.testing import CliRunner

    from jobbergate_cli.main import app as main_app

    cli_runner = CliRunner()
    captured = {}

    @main_app.command(name="probe-active-context", hidden=True)
    def probe_active_context():
        captured["context"] = get_active_context()

    try:
        result = cli_runner.invoke(main_app, ["--raw", "probe-active-context"])
    finally:
        main_app.registered_commands = [
            command for command in main_app.registered_commands if command.callback is not probe_active_context
        ]

    assert result.exit_code == 0, f"probe failed: {result.stdout}"
    assert isinstance(captured["context"], JobbergateContext)
    assert captured["context"].raw_output is True
