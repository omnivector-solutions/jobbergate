"""
Abstraction layer for questions. Each class represents different question types.

The questions describe literal questions that are asked of the user in an interactive
mode via the ``inquirer`` package.

Questions will be skipped and use the default value if the `ignore` property resolves
to True.

Questions will also resolve to their default values if running in "fast mode".
"""

from functools import partial
from itertools import chain
from typing import Any, Callable, Dict, Type, TypeVar

import inquirer
import inquirer.errors
import inquirer.questions

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
    ):
        """
        Initialize the Question.

        Args:
            variablename: The key in the config dictionary that this question will set.
            message: The message to show the user that describes what the question is gathering.
            ignore: If true, do not ask the question and just use the default value instead.
            default: The default value for the variablename in the answers dict.
            inquirer_type: The ``inquirer`` question type that this ``QuestionBase`` wraps.
        """
        self.variablename = variablename
        self.default = default
        self.inquirer_kwargs = dict(
            message=message,
            default=default,
            ignore=ignore,
        )
        self.inquirer_type = inquirer_type

    def make_prompts(self, **override_kwargs):
        """
        Create ``inquirer`` prompts from this instance of ``QuestionBase``.

        Args:
            override_kwargs: A collection of keyword arguments to override in initializing the ``inquirer`` question.
        """
        final_kwargs = {
            **self.inquirer_kwargs,
            **override_kwargs,
        }
        return [self.inquirer_type(self.variablename, **final_kwargs)]


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

    def _validator(self, _, current):
        """
        Provide a custom validator that checks the value of the integer to make sure it is in range.
        """
        try:
            int_val = int(current)
        except ValueError:
            raise inquirer.errors.ValidationError("", reason=f"{current} is not an integer")

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
        self.inquirer_kwargs.update(path_type=inquirer.Path.DIRECTORY)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)


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
        self.inquirer_kwargs.update(path_type=inquirer.Path.FILE)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)


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

        super().__init__(
            variablename,
            message + " [SPACE: Select | ENTER: Confirm | CTRL+A: Select all | CTRL+R: Unselect all]",
            inquirer_type=inquirer.Checkbox,
            **kwargs,
        )
        self.inquirer_kwargs.update(choices=choices)


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
        self.whentrue_child = whentrue or list()
        self.whenfalse_child = whenfalse or list()

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

    def make_prompts(self):
        """
        Create ``inquirer`` prompts from this instance of ``Const``.
        """
        return super().make_prompts(ignore=True)
