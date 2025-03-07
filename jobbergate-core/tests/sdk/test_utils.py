from jobbergate_core.sdk.utils import filter_null_out


def test_filter_null_out() -> None:
    """Test the filter_null_out function."""
    data = {"a": 1, "b": None, "c": 2}
    result = filter_null_out(data)
    assert result == {"a": 1, "c": 2}
