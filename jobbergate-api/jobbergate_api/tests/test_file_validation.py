import pytest

from jobbergate_api.file_validation import is_valid_python_file, is_valid_yaml_file


@pytest.mark.parametrize(
    "is_valid, source_code",
    [
        (False, "for i in range(10):\nprint(i)"),
        (True, "for i in range(10):\n    print(i)"),
    ],
)
def test_is_valid_python_file(is_valid, source_code):
    """
    Test if a given python source code is correctly checked as valid or not.
    """
    assert is_valid_python_file(source_code) is is_valid


@pytest.mark.parametrize(
    "is_valid, source_code",
    [
        (False, "unbalanced blackets: ]["),
        (True, "balanced blackets: []"),
    ],
)
def test_is_valid_yaml_file(is_valid, source_code):
    """
    Test if a given YAML file is correctly checked as valid or not.
    """
    assert is_valid_yaml_file(source_code) is is_valid
