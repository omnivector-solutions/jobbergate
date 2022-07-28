"""
Validation methods for many file formats.
"""

from ast import parse
from typing import Union

from yaml import YAMLError, safe_load


def is_valid_python_file(source_code: Union[str, bytes]) -> bool:
    """
    Check if a given Python source code is valid by parsing it into an AST node.

    :param Union[str, bytes] source_code: Python source code.
    :return bool: Boolean indicating if the source code is valid or not.
    """
    try:
        parse(source_code)
    except SyntaxError:
        return False
    return True


def is_valid_yaml_file(source_code: Union[str, bytes]) -> bool:
    """
    Check if a given YAML file is valid by parsing it with yaml.safe_load.

    :param Union[str, bytes] source_code: YAML file.
    :return bool: Boolean indicating if the source code is valid or not.
    """
    try:
        safe_load(source_code)
    except YAMLError:
        return False
    return True
