from jobbergate_api.apps.job_script_templates.tools import coerce_id_or_identifier


def test_coerce_id_or_identifier__converts_to_int():
    """
    Test that `coerce_id_or_identifier()` can convert a string representation of an integer to an int.
    """
    assert coerce_id_or_identifier("13") == 13


def test_coerce_id_or_identifier__does_not_convert_non_integer_values():
    """
    Test that `coerce_id_or_identifier()` does not non-integer values.
    """
    assert coerce_id_or_identifier("13.1") == "13.1"
    assert coerce_id_or_identifier("three") == "three"
