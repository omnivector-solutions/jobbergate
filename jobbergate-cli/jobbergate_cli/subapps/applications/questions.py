"""
Abstraction layer for questions. Each class represents different question types.
"""

from itertools import chain
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

import inquirer
import inquirer.errors
import inquirer.questions

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import render_dict


workflows = {}


TInquirerType = TypeVar("TInquirerType", bound=inquirer.questions.Question)


class QuestionBase:
    """
    Baseclass for questions.

    All questions have variablename, message and an optional default.

    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        ignore: bool = False,
        default: Optional[Any] = None,
        inquirer_type: Type[TInquirerType] = inquirer.Text,
    ):
        self.variablename = variablename
        self.default = default
        self.inquirer_kwargs = dict(
            message=message,
            default=default,
            ignore=ignore,
        )
        self.inquirer_type = inquirer_type

    def make_prompts(self, **override_kwargs):
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

    :param minval: Minimum value
    :param maxval: Maximum value
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        minval: Optional[int] = None,
        maxval: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(variablename, message, **kwargs)
        self.minval = minval
        self.maxval = maxval
        self.inquirer_kwargs.update(validate=self._validator)

    def _validator(self, _, current):
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

    :param choices: List with choices
    """

    def __init__(self, variablename: str, message: str, choices: list, **kwargs):
        super().__init__(variablename, message, inquirer_type=inquirer.List, **kwargs)
        self.inquirer_kwargs.update(choices=choices)


class Directory(QuestionBase):
    """
    Asks for a directory name. If `exists` is `True` it checks if path exists and is a directory.

    :param exists: Checks if given directory exists
    """

    def __init__(self, variablename: str, message: str, exists: Optional[bool] = None, **kwargs):
        super().__init__(variablename, message, inquirer_type=inquirer.Path, **kwargs)
        self.inquirer_kwargs.update(path_type=inquirer.Path.DIRECTORY)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)


class File(QuestionBase):
    """
    Asks for a file name. If `exists` is `True` it checks if path exists and is NOT a directory.
    """

    def __init__(self, variablename: str, message: str, exists: Optional[bool] = None, **kwargs):
        super().__init__(variablename, message, inquirer_type=inquirer.Path, **kwargs)
        self.inquirer_kwargs.update(path_type=inquirer.Path.FILE)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)


class Checkbox(QuestionBase):
    """
    Gives the user a list to choose multiple entries from.
    """

    def __init__(self, variablename: str, message: str, choices: list, **kwargs):
        super().__init__(variablename, message, inquirer_type=inquirer.Checkbox, **kwargs)
        self.inquirer_kwargs.update(choices=choices)


class Confirm(QuestionBase):
    """
    Asks a question with a boolean answer (true/false).
    """

    def __init__(self, variablename: str, message: str, **kwargs):
        super().__init__(variablename, message, inquirer_type=inquirer.Confirm, **kwargs)


class BooleanList(Confirm):
    """
    Gives the use a boolean question, and depending on answer it shows `whentrue` or `whenfalse` questions.
    `whentrue` and `whenfalse` are lists with questions. Could contain multiple levels of BooleanLists.

    :param whentrue: List of questions to show if user answers yes/true on this question
    :param whentrue: List of questions to show if user answers no/false on this question
    """

    def __init__(
        self,
        variablename: str,
        message: str,
        whentrue=None,
        whenfalse=None,
        **kwargs,
    ):
        super().__init__(variablename, message, **kwargs)
        if whentrue is None and whenfalse is None:
            raise ValueError("Empty questions lists")
        self.whentrue = whentrue
        self.whenfalse = whenfalse

        self.ignore = lambda a: a.get(variablename, True)
        self.noignore = lambda a: not a.get(variablename, False)

    def make_prompts(self, **override_kwargs):
        retval = super().make_prompts(**override_kwargs)
        if self.whenfalse is not None:
            retval.extend(chain.from_iterable(wf.make_prompts(ignore=self.ignore) for wf in self.whenfalse))
        if self.whentrue is not None:
            retval.extend(chain.from_iterable(wf.make_prompts(ignore=self.noignore) for wf in self.whentrue))
        return retval


class Const(Text):
    """
    Sets the variable to the `default` value. Doesn't show anything.

    """

    def __init__(self, variablename: str, **kwargs):
        super().__init__(variablename, "", **kwargs)

    def make_prompts(self):
        return super().make_prompts(ignore=True)


def gather_config_values(
    application,
    config: Dict[str, Any],
    supplied_params: Optional[Dict[str, Any]] = None,
    fast_mode: bool = False,
):
    """
    Gather the config values by executing the application methods.

    Prompt users for answers or use defaults as needed.
    Update the config dict in place.
    """
    if supplied_params is None:
        supplied_params = dict()
    config.update(supplied_params)

    next_method = "mainflow"

    while next_method is not None:
        method_to_call = getattr(application, next_method)

        try:
            workflow_questions = method_to_call(data=config)
        except NotImplementedError:
            raise Abort(
                f"""
                Abstract method not implemented.

                Please implement {method_to_call.__name__} in your class.",
                """,
                subject="INVALID APPLICATION MODULE",
            )

        prompts = []
        auto_answers = {}

        for question in workflow_questions:
            if question.variablename in supplied_params.keys():
                continue
            elif fast_mode and question.default is not None:
                auto_answers[question.variablename] = question.default
            else:
                prompts.extend(question.make_prompts())

        workflow_answers = cast(Dict[str, Any], inquirer.prompt(prompts, raise_keyboard_interrupt=True))
        config.update(workflow_answers)
        config.update(auto_answers)
        if len(auto_answers) > 0:
            render_dict(auto_answers, title="Default values used")

        next_method = config.pop("nextworkflow", None)
