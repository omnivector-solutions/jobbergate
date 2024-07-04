import pytest

from jobbergate_cli.auth import (
    Console,
    _show_login_narrow_screen,
    _show_login_standard_screen,
    show_login_message,
    DeviceCodeData,
)


@pytest.fixture(autouse=True)
def mocked_open_on_browser(mocker):
    """
    Provide a fixture that mocks the ``open_on_browser()`` function.
    """
    mocked = mocker.patch("jobbergate_cli.auth.open_on_browser")
    mocked.return_value = True
    return mocked


class TestShowLoginMessage:
    @pytest.fixture()
    def mocked_helpers(self, mocker):
        mocker.patch("jobbergate_cli.auth.open_on_browser", return_value=False)
        mocker.patch("jobbergate_cli.auth.copy_to_clipboard", return_value=False)

    def test_show_login_message__standard_screen(self, mocker, mocked_helpers):
        """
        Assert that the ``show_login_message()`` function will call ``_show_login_standard_screen()``.
        """
        verification_uri = "https://example.com"
        console_width = len(verification_uri) + 7

        device_code_data = DeviceCodeData(
            verification_uri_complete=verification_uri, expires_in=60, device_code="1234", interval=5
        )

        mocked_console = mocker.MagicMock()
        mocked_console.width = console_width
        mocker.patch("jobbergate_cli.auth.Console", return_value=mocked_console)

        mocked_show_on_narrow_screen = mocker.patch("jobbergate_cli.auth._show_login_narrow_screen")
        mocked_show_on_standard_screen = mocker.patch("jobbergate_cli.auth._show_login_standard_screen")

        show_login_message(device_code_data)

        assert mocked_show_on_narrow_screen.call_count == 0
        mocked_show_on_standard_screen.assert_called_once_with(verification_uri, 1)

        _show_login_standard_screen(verification_uri, 1)

    def test_show_login_message__narrow_screen(self, mocker, mocked_helpers):
        """
        Assert that the ``show_login_message()`` function will call ``_show_login_narrow_screen()``.
        """
        verification_uri = "https://example.com"
        console_width = len(verification_uri) + 7 - 1

        device_code_data = DeviceCodeData(
            verification_uri_complete=verification_uri, expires_in=60, device_code="1234", interval=5
        )

        mocked_console = mocker.MagicMock()
        mocked_console.width = console_width
        mocker.patch("jobbergate_cli.auth.Console", return_value=mocked_console)

        mocked_show_on_narrow_screen = mocker.patch("jobbergate_cli.auth._show_login_narrow_screen")
        mocked_show_on_standard_screen = mocker.patch("jobbergate_cli.auth._show_login_standard_screen")

        show_login_message(device_code_data)

        assert mocked_show_on_standard_screen.call_count == 0
        mocked_show_on_narrow_screen.assert_called_once_with(verification_uri, 1, mocked_console)

        _show_login_narrow_screen(verification_uri, 1, Console())
