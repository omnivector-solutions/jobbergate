"""
Validation methods for the uploaded files.
"""

from ast import parse as ast_parse
from collections import Counter
from functools import wraps
from pathlib import PurePath
from textwrap import dedent
from traceback import format_tb
from typing import Callable, Dict, List, Union

from buzz import Buzz, DoExceptParams, require_condition
from fastapi import HTTPException, UploadFile, status
from jinja2 import Environment
from loguru import logger
from yaml import safe_load as yaml_safe_load

from jobbergate_api.apps.applications.constants import (
    APPLICATION_CONFIG_FILE_NAME,
    APPLICATION_SOURCE_FILE_NAME,
)
from jobbergate_api.apps.applications.schemas import ApplicationConfig


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
    message_template = dedent(
        """
        {final_message}
        Error:
        ______
        {err}
        Traceback:
        ----------
        {trace}
        """
    )

    message = message_template.format(
        final_message=params.final_message,
        err=str(params.err),
        trace="\n".join(format_tb(params.trace)),
    )

    logger.error(message)

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


def perform_all_checks_on_uploaded_files(file_list: List[UploadFile]):
    """
    Loop though the check-list for uploaded files specifications.

    Individual checks will raise UploadedFilesValidationError if the business
    rules are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Preparing to perform all checks on the uploaded files")
    with UploadedFilesValidationError.handle_errors(
        "The uploaded files are invalid",
        do_except=log_error_and_raise_http_error,
        re_raise=False,
    ):
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
    def decorator(file_list: List[UploadFile]):
        return checker(file_list)

    return decorator


@register_check_uploaded_files
def check_uploaded_files_restrictions(upload_files: List[UploadFile]):
    """
    Check the list of uploaded files for filename restrictions.

    Jobbergate expects one source file, one (optional) config file and one
    or more template files.

    Raise UploadedFilesValidationError if the business rules are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    extension_counter = Counter(get_suffix(f) for f in upload_files)
    filenames = {upload.filename for upload in upload_files}

    logger.debug(f"Checking uploaded files extensions: {extension_counter=}")
    with UploadedFilesValidationError.check_expressions("Invalid file extensions") as check:
        check(
            APPLICATION_SOURCE_FILE_NAME in filenames,
            f"The application source file is missing ({APPLICATION_SOURCE_FILE_NAME})",
        )
        check(
            extension_counter[".j2"] + extension_counter[".jinja2"] >= 1,
            "missing one or more template files (.j2 and/or .jinja2)",
        )


@register_check_uploaded_files
def check_uploaded_files_content_type(file_list: List[UploadFile]):
    """
    Check the list of uploaded files to confirm they are specified as plain text.

    Raise UploadedFilesValidationError if the business rules are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files content types")
    expected = "text/plain"
    extension_list = ", ".join(syntax_validation_dispatch.keys())
    UploadedFilesValidationError.require_condition(
        all(f.content_type == expected for f in file_list if get_suffix(f) in syntax_validation_dispatch),
        f"The content of the files {extension_list} is expected to be {expected}",
    )


@register_check_uploaded_files
def check_uploaded_files_syntax(file_list: List[UploadFile]):
    """
    Check the list of uploaded files to verify their syntax.

    Raise UploadedFilesValidationError if the business rules are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files, validating source code")

    with UploadedFilesValidationError.check_expressions("Invalid syntax on uploaded file(s)") as check:
        for f in file_list:
            suffix = get_suffix(f)
            if suffix not in syntax_validation_dispatch:
                continue
            check(syntax_validation_dispatch[suffix](f.file.read()), f.filename)
            f.file.seek(0)


@register_check_uploaded_files
def check_uploaded_files_yaml_is_parsable(file_list: List[UploadFile]):
    """
    Check the list of uploaded files to verify if the yaml file agrees with the expected schema.

    Raise UploadedFilesValidationError if the business rules are not met.

    :param List[UploadFile] file_list: Upload file list.
    """
    logger.debug("Checking uploaded files, parsing yaml file")
    with UploadedFilesValidationError.handle_errors(
        "Not possible to get the configuration from the yaml file. "
        "Please, verify is all the required fields were provided."
    ):
        for f in file_list:
            if f.filename == APPLICATION_CONFIG_FILE_NAME:
                ApplicationConfig.get_from_yaml_file(f.file.read())
                f.file.seek(0)


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
        ast_parse(source_code)
    except Exception:
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
        yaml_safe_load(yaml_file)
    except Exception:
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
        Environment().parse(_template)
    except Exception:
        return False
    return True
