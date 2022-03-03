import json
import re

import pathlib
import pytest
import snick


from jobbergate_cli.exceptions import Abort
from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
)
from jobbergate_cli.subapps.job_scripts.tools import (
    validate_parameter_file,
    validate_application_data,
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


def test_validate_application_data__success():
    app_data = {
        JOBBERGATE_APPLICATION_MODULE_FILE_NAME: snick.dedent(
            """
            import sys

            print(f"Got some args, yo: {sys.argv}")
            """
        ),
        JOBBERGATE_APPLICATION_CONFIG_FILE_NAME: snick.dedent(
            """
            foo:
              bar: baz
            """
        ),
    }
    (app_module, app_config) = validate_application_data(app_data)
    assert isinstance(app_module, str)
    assert app_config == dict(foo=dict(bar="baz"))


def test_validate_application_files__fails_if_application_module_is_not_present():
    app_data = {
        JOBBERGATE_APPLICATION_CONFIG_FILE_NAME: snick.dedent(
            """
            foo:
              bar: baz
            """
        ),
    }

    match_pattern = re.compile(
        f"files fetched from the API were invalid.*does not contain {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_data(app_data)


def test_validate_application_files__fails_if_application_module_is_not_valid_python():
    app_data = {
        JOBBERGATE_APPLICATION_MODULE_FILE_NAME: "invalid python",
        JOBBERGATE_APPLICATION_CONFIG_FILE_NAME: snick.dedent(
            """
            foo:
              bar: baz
            """
        ),
    }

    match_pattern = re.compile(
        f"files fetched from the API were invalid.*not valid python",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_data(app_data)


def test_validate_application_files__fails_if_application_config_is_not_present():
    app_data = {
        JOBBERGATE_APPLICATION_MODULE_FILE_NAME: snick.dedent(
            """
            import sys

            print(f"Got some args, yo: {sys.argv}")
            """
        ),
    }

    match_pattern = re.compile(
        f"files fetched from the API were invalid.*does not contain {JOBBERGATE_APPLICATION_CONFIG_FILE_NAME}",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_data(app_data)


def test_validate_application_files__fails_if_application_config_is_not_valid_YAML():
    app_data = {
        JOBBERGATE_APPLICATION_MODULE_FILE_NAME: snick.dedent(
            """
            import sys

            print(f"Got some args, yo: {sys.argv}")
            """
        ),
        JOBBERGATE_APPLICATION_CONFIG_FILE_NAME: ":",
    }

    match_pattern = re.compile(
        f"files fetched from the API were invalid.*not valid YAML",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_data(app_data)
