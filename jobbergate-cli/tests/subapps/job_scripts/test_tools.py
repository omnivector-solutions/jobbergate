import json

import pathlib
import pytest


from jobbergate_cli.exceptions import Abort
from jobbergate_cli.subapps.job_scripts.tools import (
    validate_parameter_file,
)


def test_validate_parameter_file__success(tmp_path):
    parameter_path = tmp_path / "dummy.json"
    dummy_data = dict(
        foo="one",
        bar=2,
        baz=False,
    )
    parameter_path.write_text(json.dumps(dummy_data))
    assert validate_parameter_file(parameter_path) == dummy_data


def test_validate_parameter_file__fails_if_file_does_not_exist():
    with pytest.raises(Abort, match="does not exist"):
        validate_parameter_file(pathlib.Path("some/fake/path"))


def test_validate_parameter_file__fails_if_file_is_not_valid_json(tmp_path):
    parameter_path = tmp_path / "dummy.json"
    parameter_path.write_text("clearly not json")
    with pytest.raises(Abort, match="is not valid JSON"):
        validate_parameter_file(parameter_path)
