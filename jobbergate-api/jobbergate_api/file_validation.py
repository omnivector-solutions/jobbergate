"""
Validation methods for the uploaded files.
"""

from ast import parse
from collections import Counter
from functools import wraps
from pathlib import PurePath
from typing import Callable, Dict, List, Union

from buzz import Buzz, DoExceptParams, require_condition
from fastapi import HTTPException, UploadFile, status
from jinja2 import Template, TemplateSyntaxError
from loguru import logger
from yaml import YAMLError, safe_load


class UploadedFilesValidationError(Buzz):
    """Raise exception when facing any validation error on the uploaded files."""


def log_error_and_raise_http_error(params: DoExceptParams):
    """
    Work with ``UploadedFilesValidationError.handle_errors`` when something goes wrong.

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


CheckUploadedFilesEquation = Callable[[List[UploadFile]], None]
"""
Type alias describing the function signature used to check the uploaded files.

The functions are expected to raise UploadedFilesValidationError if any error is detected.
"""

check_uploaded_files_dispatch: List[CheckUploadedFilesEquation] = []
"""List the function used to check the uploaded files."""


def perform_all_checks_on_uploaded_files(file_list: List[UploadFile]) -> None:
    """
    Loop though the check-list for uploaded files specifications.

    Individual checks will raise UploadedFilesValidationError if the business
    roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Preparing to perform all checks on the uploaded files")
    for check in check_uploaded_files_dispatch:
        check(file_list)


def register_check_uploaded_files(checker: CheckUploadedFilesEquation) -> CheckUploadedFilesEquation:
    """
    Use this decorator to register functions to check the uploaded files.

    It creates a new entry on ``check_uploaded_files_dispatch``.

    :return CheckUploadedFilesEquation: The decorated function.
    """
    check_uploaded_files_dispatch.append(checker)

    @wraps(checker)
    def decorator(file_list: List[UploadFile]) -> None:
        return checker(file_list)

    return decorator


@register_check_uploaded_files
def check_uploaded_files_extensions(file_list: List[UploadFile]) -> None:
    """
    Check the list of uploaded files to count the file extensions.

    Raise UploadedFilesValidationError if the business roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    extension_counter = Counter(get_suffix(f) for f in file_list)
    logger.debug(f"Checking uploaded files extensions: {extension_counter=}")
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
        assert extension_counter[".py"] == 1
        assert extension_counter[".yaml"] in {0, 1}
        assert extension_counter[".j2"] + extension_counter[".jinja2"] >= 1


@register_check_uploaded_files
def check_uploaded_files_content_type(file_list: List[UploadFile]) -> None:
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
            f" The content of the files {', '.join(syntax_validation_dispatch.keys())}"
            f" is expected to be {expected}."
        ),
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
        assert all(
            f.content_type == expected for f in file_list if get_suffix(f) in syntax_validation_dispatch
        )


@register_check_uploaded_files
def check_uploaded_files_syntax(file_list: List[UploadFile]) -> None:
    """
    Check the list of uploaded files to verify their syntax.

    Raise UploadedFilesValidationError if the business roles are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files, validating source code")
    list_of_problems = []
    for f in file_list:
        suffix = get_suffix(f)
        if suffix not in syntax_validation_dispatch:
            continue
        if not syntax_validation_dispatch[suffix](f.file.read()):
            list_of_problems.append(f.filename)
        f.file.seek(0)
    with UploadedFilesValidationError.handle_errors(
        f"Invalid syntax on the uploaded file(s): {', '.join(list_of_problems)}",
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
        assert len(list_of_problems) == 0


SyntaxValidationEquation = Callable[[Union[str, bytes]], bool]
"""Type alias describing the function signature used to validate file syntax."""

syntax_validation_dispatch: Dict[str, SyntaxValidationEquation] = {}
"""Dictionary mapping file extensions to the function used to validate their syntax."""


def register_syntax_validator(*file_extensions: str):
    """
    Use this decorator to register file syntax validation functions.

    It creates a new entry on ``validation_dispatch``, mapping the equation to
    the file extensions that are provided as arguments.

    Raise ValueError if the provided file extensions do not start with a dot.

    :return ValidationEquation: The decorated function.
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

    :param Union[str, bytes] source_code: Python source code.
    :return bool: Boolean indicating if the source code is valid or not.
    """
    try:
        parse(source_code)
    except SyntaxError:
        return False
    return True


@register_syntax_validator(".yaml")
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


@register_syntax_validator(".j2", ".jinja2")
def is_valid_jinja2_template(template: Union[str, bytes]) -> bool:
    """
    Check if a given jinja2 template is valid by creating a Template object and trying to render it.

    :param str template: Jinja2 template.
    :return bool: Boolean indicating if the template is valid or not.
    """
    if isinstance(template, bytes):
        _template = template.decode("utf-8")
    else:
        _template = template
    try:
        Template(_template).render(data={})
    except TemplateSyntaxError:
        return False
    return True
