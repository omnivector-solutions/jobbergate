import re
from unittest import mock

import pytest

from jobbergate_cli.auth import show_login_message, track_login_progress
from jobbergate_cli.context import JobbergateContext
from jobbergate_cli.config import settings
from jobbergate_cli.exceptions import Abort


@mock.patch("jobbergate_cli.context.Client")
def test_client_is_lazy_on_context(mocked_client, tweak_settings):
    ctx = JobbergateContext()

    mocked_client.assert_not_called()

    local_settings = dict(ARMADA_API_BASE="test.example.com/", JOBBERGATE_REQUESTS_TIMEOUT=42)

    with tweak_settings(**local_settings):
        client = ctx.client

    assert client == mocked_client.return_value

    mocked_client.assert_called_once_with(
        base_url=local_settings["ARMADA_API_BASE"],
        auth=ctx.authentication_handler,
        timeout=local_settings["JOBBERGATE_REQUESTS_TIMEOUT"],
    )


@mock.patch("jobbergate_cli.context.JobbergateAuthHandler")
def test_authentication_handler_is_lazy_on_context(mocked_auth_handler, tweak_settings):
    ctx = JobbergateContext()

    mocked_auth_handler.assert_not_called()

    local_settings = dict(
        OIDC_USE_HTTPS=True,
        OIDC_DOMAIN="example.com",
        OIDC_CLIENT_ID="client-id",
        OIDC_CLIENT_SECRET="client-secret",
    )

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

    local_settings = dict(
        OIDC_DOMAIN="example.com",
        OIDC_CLIENT_ID="client-id",
        OIDC_CLIENT_SECRET="client-secret",
    )

    local_settings[missing_setting] = None

    with tweak_settings(**local_settings):
        with pytest.raises(
            Abort,
            match=re.compile(
                f"The following settings are required to enable authenticated requests:.*{missing_setting}$",
                flags=re.DOTALL,
            ),
        ):
            ctx.authentication_handler

    mocked_auth_handler.assert_not_called()
