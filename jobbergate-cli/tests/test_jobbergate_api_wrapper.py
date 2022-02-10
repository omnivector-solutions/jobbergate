"""
Tests of the API client architecture and related functions
"""

from pytest import mark

from jobbergate_cli import jobbergate_api_wrapper


@mark.parametrize(
    "input,expected",
    [
        ["hello world", "hello world"],
        ["\nhello world\n", "hello world"],
        ["hello world\nhello world", "hello world..."],
        ["hello world \nhello world", "hello world..."],
        ["hello world how are you?", "hello world..."],
        ["\nhello world how are you?\n2", "hello world..."],
    ],
    ids=["plain", "strip-ws", "short-nl", "short-nl-ws", "long", "long-nl"],
)
def test_fit_line(input, expected):
    """
    Do we truncate a string in the expected ways?
    """
    assert jobbergate_api_wrapper._fit_line(input, n=19) == expected
