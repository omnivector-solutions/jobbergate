"""
Validation methods for the uploaded files.
"""

from ast import parse as ast_parse
from functools import wraps
from pathlib import PurePath
from typing import BinaryIO, Callable, Union

from buzz import require_condition
from jinja2 import Environment
from loguru import logger
from yaml import safe_load as yaml_safe_load


def get_suffix(filename: str) -> str:
    """
    Get the suffix (file extension) from a given filename.
    """
    return PurePath(filename).suffix


def check_uploaded_file_syntax(file_obj: BinaryIO, filename: str) -> bool:
    """
    Check the syntax of a given file.
    """
    logger.debug(f"Validating source code on {filename=}")
    suffix = get_suffix(filename)
    if suffix in syntax_validation_dispatch:
        validator = syntax_validation_dispatch[suffix]
        result = validator(file_obj.read())
        file_obj.seek(0)
        return result
    logger.debug(f"Skipping because {suffix} has no syntax validation")
    return True


SyntaxValidationEquation = Callable[[Union[str, bytes]], bool]
"""Type alias describing the function signature used to validate file syntax."""

syntax_validation_dispatch: dict[str, SyntaxValidationEquation] = {}
"""Dictionary mapping file extensions to the function used to validate their syntax."""


def register_syntax_validator(*file_extensions: str):
    """
    Use this decorator to register file syntax validation functions.

    It creates a new entry on ``validation_dispatch``, mapping the equation to
    the file extensions that are provided as arguments.

    Raise ValueError if the provided file extensions do not start with a dot.
    """

    def decorator(validator):
        for extension in file_extensions:
            require_condition(
                extension.startswith("."),
                f"File extensions should start with a dot, got the value: {extension}",
                raise_exc_class=ValueError,
            )
            syntax_validation_dispatch[extension] = validator

        @wraps(validator)
        def wrapper(source_code):
            return validator(source_code)

        return wrapper

    return decorator


@register_syntax_validator(".py")
def is_valid_python_file(source_code: Union[str, bytes]) -> bool:
    """
    Check if a given Python source code is valid by parsing it into an AST node.

    Args:
        source_code: Python source code.

    Returns:
        Boolean indicating if the source code is valid or not.
    """
    try:
        ast_parse(source_code)
    except Exception:
        return False
    return True


@register_syntax_validator(".yaml")
def is_valid_yaml_file(yaml_file: Union[str, bytes]) -> bool:
    """
    Check if a given YAML file is valid by parsing it with yaml.safe_load.

    Args:
        yaml_file: YAML file.

    Returns:
        Boolean indicating if the file is valid or not.
    """
    try:
        yaml_safe_load(yaml_file)
    except Exception:
        return False
    return True


@register_syntax_validator(".j2", ".jinja2")
def is_valid_jinja2_template(template: Union[str, bytes]) -> bool:
    """
    Check if a given jinja2 template is valid by creating a Template object and trying to render it.

    Args:
        template: Jinja2 template.

    Returns:
        Boolean indicating if the template is valid or not.
    """
    if isinstance(template, bytes):
        _template = template.decode("utf-8")
    else:
        _template = template

    try:
        Environment().parse(_template)
    except Exception:
        return False
    return True
