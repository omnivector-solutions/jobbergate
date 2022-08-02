"""
Test the components used to validate the uploaded files.
"""

import pytest
from fastapi import UploadFile

from jobbergate_api.file_validation import (
    check_uploaded_files_dispatch,
    get_suffix,
    is_valid_jinja2_template,
    is_valid_python_file,
    is_valid_yaml_file,
    syntax_validation_dispatch,
)


@pytest.mark.parametrize(
    "filename, suffix",
    [
        ("jobbergate.py", ".py"),
        ("jobbergate.yaml", ".yaml"),
        ("jobbergate.py.jinja2", ".jinja2"),
        ("jobbergate.py.j2", ".j2"),
    ],
)
def test_get_suffix(filename, suffix, make_dummy_file):
    """
    Test if the file suffix is correctly from an UploadFile.
    """
    dummy_file = make_dummy_file(filename)
    dummy_upload = UploadFile(filename, file=dummy_file)
    assert get_suffix(dummy_upload) == suffix


@pytest.mark.parametrize(
    "is_valid, source_code",
    [
        (False, "for i in range(10):\nprint(i)"),
        (True, "for i in range(10):\n    print(i)"),
        # Notice it does not catch counter as an unknown variable
        (True, "for i in range(counter):\n    print(i)"),
    ],
)
def test_is_valid_python_file(is_valid, source_code):
    """
    Test if a given python source code is correctly checked as valid or not.
    """
    assert is_valid_python_file(source_code) is is_valid


@pytest.mark.parametrize(
    "is_valid, yaml_file",
    [
        (False, "unbalanced blackets: ]["),
        (True, "balanced blackets: []"),
    ],
)
def test_is_valid_yaml_file(is_valid, yaml_file):
    """
    Test if a given YAML file is correctly checked as valid or not.
    """
    assert is_valid_yaml_file(yaml_file) is is_valid


@pytest.mark.parametrize(
    "is_valid, template",
    [
        (False, "Hello {{ name }!"),
        (True, "Hello {{ name }}!"),
    ],
)
def test_is_valid_jinja2_template(is_valid, template):
    """
    Test if a given python source code is correctly checked as valid or not.
    """
    assert is_valid_jinja2_template(template) is is_valid


def test_check_uploaded_files_dispatch__length():
    """
    Test if the number of element is the expected.
    """
    assert len(check_uploaded_files_dispatch) == 3


def test_syntax_validation_dispatch__length():
    """
    Test if the number of elements is the expected.
    """
    assert len(syntax_validation_dispatch) == 4
