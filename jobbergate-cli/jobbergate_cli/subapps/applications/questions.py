"""
Abstraction layer for questions. Each class represents different question types.

The questions describe literal questions that are asked of the user in an interactive
mode via the ``inquirer`` package.

Questions will be skipped and use the default value if the `ignore` property resolves
to True.

Questions will also resolve to their default values if running in "fast mode".
"""

import os
from functools import partial
from itertools import chain
from typing import Any, Callable, Dict, Optional, Type, TypeVar

import inquirer
import inquirer.errors
import inquirer.questions
import jsonschema

from jobbergate_cli.exceptions import Abort

TInquirerType = TypeVar("TInquirerType", bound=inquirer.questions.Question)


class QuestionBase:
    """
    Baseclass for questions.

    All questions have variablename, message and an optional default.
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        ignore: bool = False,
        default: Any | None = None,
        inquirer_type: Type[TInquirerType] = inquirer.Text,
        schema: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            ignore: If true, do not ask the question and just use the default value instead.
            default: The default value for the variablename in the answers dict.
            inquirer_type: The ``inquirer`` question type that this ``QuestionBase`` wraps.
            schema: Optional `JSON Schema <https://json-schema.org>`_ constraints for the
                answer (e.g. ``{"pattern": ...}``, ``{"maxLength": ...}``). They are merged
                over the constraints the question type generates on its own (see
                :meth:`json_schema`) and enforced as an extra validator wherever the
                question is asked — terminal or web form alike.
        """
        self.variablename = variablename
        self.default = default
        self.schema = schema
        self.message = message
        self.inquirer_kwargs = {
            "message": message,
            "default": default,
            "ignore": ignore,
        }
        self.inquirer_type = inquirer_type

    def base_schema(self) -> Dict[str, Any]:
        """
        The JSON Schema fragment describing this question type's answer.

        Subclasses override this to express their own constraints (integer ranges, choice
        enums, and so on), making the schema the single source of truth that both the
        validators and any auto-generated front-end share.
        """
        return {"type": "string"}

    def json_schema(self) -> Dict[str, Any]:
        """
        The full JSON Schema for this question's answer.

        Combines the type's :meth:`base_schema` with the user-supplied ``schema`` overrides,
        plus ``title`` (the message) and ``default`` annotations.
        """
        schema: Dict[str, Any] = {"title": self.message or self.variablename}
        schema.update(self.base_schema())
        if self.default is not None:
            schema["default"] = self.default
        if self.schema:
            schema.update(self.schema)
        return schema

    def coerce_answer(self, value: Any) -> Any:
        """
        Coerce a raw answer toward the schema's declared type before validation.

        Interactive backends deliver every value as a string (that is how terminals work),
        so ``"3"`` must count as a valid integer answer.
        """
        declared = self.json_schema().get("type")
        if isinstance(value, str):
            try:
                if declared == "integer":
                    return int(value)
                if declared == "number":
                    return float(value)
            except ValueError:
                return value
        elif declared == "string" and isinstance(value, os.PathLike):
            return str(value)
        return value

    def _schema_validator(self, answers: Dict[str, Any], current: Any) -> bool:
        """Validate an answer against :meth:`json_schema`; the last say stays with the runtime."""
        try:
            jsonschema.validate(self.coerce_answer(current), self.json_schema())
        except jsonschema.ValidationError as err:
            raise inquirer.errors.ValidationError("", reason=err.message) from err
        return True

    def _combined_validator(self, prior: Any) -> Callable[[Dict[str, Any], Any], bool]:
        """Chain a preexisting inquirer validator (callable or bool) with the schema check."""

        def validate(answers: Dict[str, Any], current: Any) -> bool:
            if callable(prior):
                if not prior(answers, current):
                    raise inquirer.errors.ValidationError("", reason=f"{current!r} is not a valid value")
            elif not prior:
                raise inquirer.errors.ValidationError("", reason=f"{current!r} is not a valid value")
            return self._schema_validator(answers, current)

        return validate

    def make_prompts(self, **override_kwargs):
        """
        Create ``inquirer`` prompts from this instance of ``QuestionBase``.

        The resulting prompts validate against :meth:`json_schema` (after any imperative
        validator the question type defines, so their messages take precedence) and carry
        the schema as ``jobbergate_schema`` for wire serialization.

        Args:
            override_kwargs: A collection of keyword arguments to override in initializing the ``inquirer`` question.
        """
        final_kwargs = {
            **self.inquirer_kwargs,
            **override_kwargs,
        }
        final_kwargs["validate"] = self._combined_validator(final_kwargs.get("validate", True))
        prompt = self.inquirer_type(self.variablename, **final_kwargs)
        prompt.jobbergate_schema = self.json_schema()
        return [prompt]


class Text(QuestionBase):
    """
    Asks for a text value.
    """


class Integer(QuestionBase):
    """
    Asks for an integer value. Could have min and/or max constrains.
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        minval: int | None = None,
        maxval: int | None = None,
        **kwargs,
    ):
        """
        Initialize the Integer question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            minval: The minimum value the integer may be set to. If not specified, use negative infinity.
            maxval: The maximum value the integer may be set to. If not specified, use infinity.
        """
        super().__init__(variablename, message, **kwargs)
        self.minval = minval
        self.maxval = maxval
        if self.inquirer_kwargs.get("default") == 0:
            self.inquirer_kwargs["default"] = "0"
        self.inquirer_kwargs.update(validate=self._validator)

    def base_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "integer"}
        if self.minval is not None:
            schema["minimum"] = self.minval
        if self.maxval is not None:
            schema["maximum"] = self.maxval
        return schema

    def _validator(self, _, current):
        """
        Provide a custom validator that checks the value of the integer to make sure it is in range.
        """
        try:
            int_val = int(current)
        except ValueError as err:
            raise inquirer.errors.ValidationError("", reason=f"{current} is not an integer") from err

        min_str = str(self.minval) if self.minval is not None else "-∞"
        max_str = str(self.maxval) if self.maxval is not None else "∞"
        if any(
            [
                self.minval is not None and int_val < self.minval,
                self.maxval is not None and int_val > self.maxval,
            ]
        ):
            raise inquirer.errors.ValidationError("", reason=f"{current} is out of range [{min_str}, {max_str}]")
        return True


class List(QuestionBase):
    """
    Gives the user a list to choose one from.
    """

    def __init__(self, variablename: str, message: str, choices: list, **kwargs):
        """
        Initialize the List question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            choices: A list of the possible values from which the Question will allow the user to select one.
        """
        super().__init__(variablename, message, inquirer_type=inquirer.List, **kwargs)
        self.inquirer_kwargs.update(choices=choices)

    def base_schema(self) -> Dict[str, Any]:
        return {"enum": list(self.inquirer_kwargs["choices"])}


class Directory(QuestionBase):
    """
    Asks for a directory name. If `exists` is `True`, it checks if the path exists and is a directory.

    Args:
        exists: Checks if the given directory exists.
    """

    def __init__(self, variablename: str, message: str, exists: bool | None = None, **kwargs):
        """
        Initialize the Directory question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            exists: If True, ensure that the directory exists on the system.
        """

        super().__init__(variablename, message, inquirer_type=inquirer.Path, **kwargs)
        self.exists = exists
        self.inquirer_kwargs.update(path_type=inquirer.Path.DIRECTORY)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)

    def base_schema(self) -> Dict[str, Any]:
        # The existence check cannot be expressed in JSON Schema (it runs against the
        # filesystem where the runtime executes); the x- annotations let a front-end hint it
        schema: Dict[str, Any] = {"type": "string", "x-path-type": "directory"}
        if self.exists is not None:
            schema["x-exists"] = self.exists
        return schema


class File(QuestionBase):
    """
    Asks for a file name.
    """

    def __init__(self, variablename: str, message: str, exists: bool | None = None, **kwargs):
        """
        Initialize the File question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            exists: If True, ensure that the file path exists on the system.
        """
        super().__init__(variablename, message, inquirer_type=inquirer.Path, **kwargs)
        self.exists = exists
        self.inquirer_kwargs.update(path_type=inquirer.Path.FILE)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)

    def base_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "string", "x-path-type": "file"}
        if self.exists is not None:
            schema["x-exists"] = self.exists
        return schema


class Checkbox(QuestionBase):
    """
    Gives the user a list to choose multiple entries from.
    """

    def __init__(self, variablename: str, message: str, choices: list, **kwargs):
        """
        Initialize the Checkbox question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            choices: A list of the possible values from which the Question will allow the user to select many.
        """

        super().__init__(variablename, message, inquirer_type=inquirer.Checkbox, **kwargs)
        # The keybinding hint is terminal-only: it decorates the inquirer prompt but stays
        # out of self.message (and therefore out of the JSON Schema title shown on the web)
        self.inquirer_kwargs["message"] = (
            message + " [SPACE: Select | ENTER: Confirm | CTRL+A: Select all | CTRL+R: Unselect all]"
        )
        self.inquirer_kwargs.update(choices=choices)

    def base_schema(self) -> Dict[str, Any]:
        return {
            "type": "array",
            "items": {"enum": list(self.inquirer_kwargs["choices"])},
            "uniqueItems": True,
        }


class Confirm(QuestionBase):
    """
    Asks a question with a boolean answer (true/false).
    """

    def __init__(self, variablename: str, message: str, **kwargs):
        """
        Initialize the Confirm question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
        """
        super().__init__(variablename, message, inquirer_type=inquirer.Confirm, **kwargs)

    def base_schema(self) -> Dict[str, Any]:
        return {"type": "boolean"}


class BooleanList(Confirm):
    """
    Asks a confirmation question that is followed up by a certain question list when true and a different list if false.
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        whentrue=None,
        whenfalse=None,
        **kwargs,
    ):
        """
        Initialize the Checkbox question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            whentrue: List of questions to ask if the user answers 'true' on this question.
            whenfalse: List of questions to show if the user answers 'false' on this question.
        """
        super().__init__(variablename, message, **kwargs)
        self.whentrue_child = whentrue or []
        self.whenfalse_child = whenfalse or []

    def ignore_child(self, child: QuestionBase, answers: dict[str, Any]) -> bool:
        """
        Dynamically check if a child question should be ignored based on the questions that have already been answered.

        Args:
            child: The child question that might be ignored.
            answers: Answer values to previously asked questions.
        """
        my_answer = answers.get(self.variablename)
        Abort.require_condition(
            my_answer is not None,
            "Questions were asked out of order. Please check your Application for consistency",
        )
        if (my_answer is True and child in self.whenfalse_child) or (
            my_answer is False and child in self.whentrue_child
        ):
            return True
        return False

    def make_ignore_partial(self, child: QuestionBase) -> Callable[[Dict[str, Any]], bool]:
        """
        Build a partial method for checking if a child should be ignored.

        This method just makes the code more readable so that a non-descriptive lambda does not need to be used inline.
        """
        return partial(self.ignore_child, child)

    def make_prompts(self, **override_kwargs):
        """
        Create ``inquirer`` prompts from this instance of ``BooleanList`` and for all its child questions.

        Args:
            override_kwargs: A collection of keyword arguments to override in the base ``make_prompts`` method.
        """

        retval = super().make_prompts(**override_kwargs)
        for child in chain(self.whentrue_child, self.whenfalse_child):
            retval.extend(child.make_prompts(ignore=self.make_ignore_partial(child)))
        return retval


class Const(Text):
    """
    Sets the variable to the `default` value. Doesn't show anything.
    """

    def __init__(self, variablename: str, **kwargs):
        """
        Initialize the Const "question".

        Args:
            variablename: The key in the config dictionary that this question will set.
        """
        super().__init__(variablename, "", **kwargs)

    def base_schema(self) -> Dict[str, Any]:
        return {"const": self.default}

    def make_prompts(self):
        """
        Create ``inquirer`` prompts from this instance of ``Const``.
        """
        return super().make_prompts(ignore=True)
