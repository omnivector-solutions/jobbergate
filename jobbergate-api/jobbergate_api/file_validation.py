"""
Validation methods for uploaded files.
"""

from ast import parse
from collections import Counter
from functools import wraps
from pathlib import PurePath
from typing import Callable, Dict, List, Union

from buzz import Buzz, require_condition, DoExceptParams
from fastapi import HTTPException, UploadFile, status
from jinja2 import Template, TemplateSyntaxError
from loguru import logger
from yaml import YAMLError, safe_load


class UploadedFilesValidationError(Buzz):
    """Raise exception when faces any validation error on the uploaded files."""


def log_error_and_raise_http_error(params: DoExceptParams):
    """
    Work with `UploadedFilesValidationError.handle_errors` when something goes wrong.

    In case any error occurs in the context manager, the error is logged and
    a HTTPException is raised.

    :param DoExceptParams params: Params from handle_errors.
    :raises HTTPException: Code 422, unprocessable entity.
    """
    logger.error(params.final_message)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=params.final_message)


def get_suffix(file: UploadFile) -> str:
    """
    Get the suffix (file extension) of an UploadFile.

    :param UploadFile file: Target file.
    :return str: File extension.
    """
    return PurePath(file.filename).suffix


def check_uploaded_files(file_list: List[UploadFile]):
    """
    Loop though the check-list for uploaded files specifications.

    :param List[UploadFile] file_list: Upload file list.
    """
    check_list = [
        check_uploaded_files_extensions,
        check_uploaded_files_content_type,
        check_uploaded_files_code,
    ]
    for check in check_list:
        check(file_list)


def check_uploaded_files_extensions(file_list: List[UploadFile]):
    """
    Check the list of uploaded files to count the file extensions.

    Raise UploadedFilesValidationError if the business roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files extensions")
    extension_counter = Counter(get_suffix(f) for f in file_list)
    with UploadedFilesValidationError.handle_errors(
        (
            "Error while validating the extension of the uploaded files."
            " For the application files, the specification is:"
            " One application source file (.py);"
            " One (optional) application config file (.yaml);"
            " One or more template files (.j2 and/or .jinja2)."
        ),
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
        assert extension_counter.get(".py", 0) == 1
        assert extension_counter.get(".yaml", 0) in {0, 1}
        assert extension_counter.get(".j2", 0) + extension_counter.get(".jinja2", 0) >= 1


def check_uploaded_files_content_type(file_list: List[UploadFile]) -> bool:
    """
    Check the list of uploaded files to confirm they are specified as plain text.

    Raise UploadedFilesValidationError if the business roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files content types")
    expected = "text/plain"
    with UploadedFilesValidationError.handle_errors(
        (
            "Error while validating the content type of the uploaded files."
            f" The content of the files {', '.join(validation_dispatch.keys())}"
            f" is expected to be {expected}."
        ),
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
        assert all(f.content_type == expected for f in file_list if get_suffix(f) in validation_dispatch)


def check_uploaded_files_code(file_list: List[UploadFile]) -> bool:
    """
    Check the list of uploaded files to verify their syntax.

    Raise UploadedFilesValidationError if the business roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files, validating source code")
    list_of_problems = []
    for f in file_list:
        if not validation_dispatch.get(get_suffix(f), lambda _: True)(f.file):
            list_of_problems.append(f.filename)
    with UploadedFilesValidationError.handle_errors(
        f"Invalid syntax on the uploaded file(s): {', '.join(list_of_problems)}",
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
        assert len(list_of_problems) == 0


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
