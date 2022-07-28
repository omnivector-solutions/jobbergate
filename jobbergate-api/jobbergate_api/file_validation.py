"""
Validation methods for many file formats.
"""

from ast import parse
from typing import Union

from jinja2 import Template, TemplateSyntaxError
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


def is_valid_yaml_file(yaml_file: Union[str, bytes]) -> bool:
    """
    Check if a given YAML file is valid by parsing it with yaml.safe_load.

    :param Union[str, bytes] yaml_file: YAML file.
    :return bool: Boolean indicating if the file is valid or not.
    """
    try:
        safe_load(yaml_file)
    except YAMLError:
        return False
    return True


def is_valid_jinja2_template(template: Union[str, bytes]) -> bool:
    """
    Check if a given jinja2 template is valid by creating a Template object and trying to render it.

    :param Union[str, bytes] template: Jinja2 template.
    :return bool: Boolean indicating if the template is valid or not.
    """
    try:
        Template(template).render(data={})
    except TemplateSyntaxError:
        return False
    return True
