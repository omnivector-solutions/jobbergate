"""
Validation methods for many file formats.
"""

from ast import parse
from collections import Counter
from functools import wraps
from pathlib import PurePath
from typing import Callable, Dict, List, Union

from buzz import Buzz, require_condition
from fastapi import UploadFile
from jinja2 import Template, TemplateSyntaxError
from loguru import logger
from yaml import YAMLError, safe_load


class UploadedFilesValidationError(Buzz):
    """Raise exception when faces any validation error on the uploaded files."""

def check_uploaded_files_extensions(file_list: List[UploadFile]) -> bool:
    """
    Check the list of uploaded files to verify business rules.

    For the application files, it means:
    * One application source file (.py);
    * One (optional) application config file (.yaml);
    * One or more template files (.j2 and/or .jinja2).

    :param List[UploadFile] file_list: Upload file list.
    :return bool: Result of the tests.
    """
    logger.debug("Checking uploaded files extensions")
    extension_counter = Counter(PurePath(f.filename).suffix for f in file_list)
    try:
        assert extension_counter.get(".py", 0) == 1
        assert extension_counter.get(".yaml", 0) in {0, 1}
        assert extension_counter.get(".j2", 0) + extension_counter.get(".jinja2", 0) >= 1
    except AssertionError:
        return False
    return True
ValidationEquation = Callable[[Union[str, bytes]], bool]
"""Type alias describing the function signature used to validate the files."""

validation_dispatch: Dict[str, ValidationEquation] = {}
"""Dictionary mapping file extensions to the function used to validate them."""


def register(*file_extensions: str) -> ValidationEquation:
    """
    Use this decorator to register validation functions.

    It creates a new entry on ``validation_dispatch``, mapping the equation to
    the file extensions that are provided as arguments.

    Raise ValueError if the provided file extensions do not start with a dot.

    :return ValidationEquation: The validation equation.
    """

    def decorator(validator: ValidationEquation) -> ValidationEquation:
        for extension in file_extensions:
            require_condition(
                extension.startswith("."),
                "File extensions are expected to start with a dot.",
                raise_exc_class=ValueError,
            )
            validation_dispatch[extension] = validator

        @wraps(validator)
        def wrapper(*args, **kwargs):
            return validator(*args, **kwargs)

        return wrapper

    return decorator


@register(".py")
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


@register(".yaml")
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


@register(".j2", ".jinja2")
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
