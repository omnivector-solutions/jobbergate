from pathlib import Path
import pytest
from click import UsageError
from jobbergate_cli.subapps.tools import resolve_application_selection, resolve_selection


class TestResolveApplicationSelection:
    def test_resolve_application_selection_digit(self):
        assert resolve_application_selection(id_or_identifier="123") == 123

    def test_resolve_application_selection_string(self):
        assert resolve_application_selection(id_or_identifier="app-identifier") == "app-identifier"

    def test_resolve_application_selection_identifier_only(self):
        assert resolve_application_selection(identifier="app-identifier") == "app-identifier"

    def test_resolve_application_selection_id_only(self):
        assert resolve_application_selection(id=456) == 456

    def test_resolve_application_selection_all_null(self):
        with pytest.raises(UsageError, match="^You must supply one and only one selection value"):
            resolve_application_selection(id_or_identifier=None, id=None, identifier=None)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"id_or_identifier": "123", "id": 456},
            {"id_or_identifier": "123", "identifier": "app-identifier"},
            {"id": 456, "identifier": "app-identifier"},
        ],
    )
    def test_resolve_application_selection_multiple_args(self, kwargs):
        with pytest.raises(UsageError, match="^You must supply one and only one selection value"):
            resolve_application_selection(**kwargs)


class TestResolveSelection:
    @pytest.mark.parametrize("value", [10, "value", Path("test-test")])
    def test_resolve_selection_single_value(self, value):
        assert resolve_selection(None, value, None) == value

    def test_resolve_selection_no_arguments(self):
        with pytest.raises(UsageError, match="^You must supply one and only one selection value"):
            resolve_selection(option_name="test")

    def test_resolve_selection_all_null(self):
        with pytest.raises(UsageError, match="^You must supply one and only one selection value") as exec_info:
            resolve_selection(None, None, None, option_name="test_option")

        expected_message = "You must supply one and only one selection value (positional test_option or --test-option)"
        assert exec_info.value.message == expected_message

    @pytest.mark.parametrize("value", [10, "value", Path("test-test")])
    def test_resolve_selection_multiple_values(self, value):
        with pytest.raises(UsageError, match="^You must supply one and only one selection value"):
            resolve_selection(value, value)
