from jobbergate_cli.text_tools import copy_to_clipboard


def test_copy_to_clipboard__success(mocker):
    """
    Validate that the ``copy_to_clipboard`` function calls ``pyperclip.copy`` successfully and returns ``True``.
    """
    mocked_copy = mocker.patch("pyperclip.copy")
    assert copy_to_clipboard("some text")
    mocked_copy.assert_called_once_with("some text")


def test_copy_to_clipboard__does_not_raise_exception_on_failure(mocker):
    """
    Validate that the ``copy_to_clipboard`` function catches exceptions from ``pyperclip.copy`` and returns ``False``.
    """
    mocked_copy = mocker.patch("pyperclip.copy", side_effect=RuntimeError("BOOM!!!"))
    assert not copy_to_clipboard("some text")
    mocked_copy.assert_called_once_with("some text")
