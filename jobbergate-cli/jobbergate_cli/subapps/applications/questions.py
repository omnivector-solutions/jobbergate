"""
Abstraction layer for questions. Each class represents different question types.

The questions describe literal questions that are asked of the user in an interactive
mode via the ``inquirer`` package.

Questions will be skipped and use the default value if the `ignore` property resolves
to True.

Questions will also resolve to their default values if running in "fast mode".
"""

from copy import deepcopy
from functools import partial
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

import inquirer
import inquirer.errors
import inquirer.questions

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.render import render_dict
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase


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
        default: Optional[Any] = None,
        inquirer_type: Type[TInquirerType] = inquirer.Text,
    ):
        """
        Initialize the Question.

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: ignore:        If true, do not ask the question and just use the default value instead
        :param: default:       The default value for the variablename in the answers dict
        :param: inquirer_type: The ``inquirer`` question type that this ``QuestionBase`` wraps
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

        :param: override_kwargs: A collection of keyword arguments to override in intializing the ``inquirer`` question
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
        minval: Optional[int] = None,
        maxval: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize the Integer question.

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: minval:        The minimum value the integer may be set to. If not specified, use negative infinity.
        :param: minval:        The maximum value the integer may be set to. If not specified, use infinity.
        """
        super().__init__(variablename, message, **kwargs)
        self.minval = minval
        self.maxval = maxval
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

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: choices:       A list of the possible values from which the Question will allow the user to select one
        """
        super().__init__(variablename, message, inquirer_type=inquirer.List, **kwargs)
        self.inquirer_kwargs.update(choices=choices)


class Directory(QuestionBase):
    """
    Asks for a directory name. If `exists` is `True` it checks if path exists and is a directory.

    :param exists: Checks if given directory exists
    """

    def __init__(self, variablename: str, message: str, exists: Optional[bool] = None, **kwargs):
        """
        Initialize the Directory question.

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: exists:        If True, ensure that the directory exists on the system
        """

        super().__init__(variablename, message, inquirer_type=inquirer.Path, **kwargs)
        self.inquirer_kwargs.update(path_type=inquirer.Path.DIRECTORY)
        if exists is not None:
            self.inquirer_kwargs.update(exists=exists)


class File(QuestionBase):
    """
    Asks for a file name.
    """

    def __init__(self, variablename: str, message: str, exists: Optional[bool] = None, **kwargs):
        """
        Initialize the File question.

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: exists:        If True, ensure that the file path exists on the system
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

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param: choices:       A list of the possible values from which the Question will allow the user to select many
        """

        super().__init__(variablename, message, inquirer_type=inquirer.Checkbox, **kwargs)
        self.inquirer_kwargs.update(choices=choices)


class Confirm(QuestionBase):
    """
    Asks a question with a boolean answer (true/false).
    """

    def __init__(self, variablename: str, message: str, **kwargs):
        """
        Initialize the Confirm question.

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
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

        :param: variablename:  The key in the config dictionary that this question will set
        :param: message:       The message to show the user that describes what the question is gathering
        :param whentrue:       List of questions to ask if user answers 'true' on this question
        :param whentrue:       List of questions to show if user answers 'false' on this question
        """
        super().__init__(variablename, message, **kwargs)
        self.whentrue_child_map = {c.variablename: c for c in (whentrue if whentrue is not None else [])}
        self.whenfalse_child_map = {c.variablename: c for c in (whenfalse if whenfalse is not None else [])}

    def ignore_child(self, child: QuestionBase, answers: Dict[str, Any]) -> bool:
        """
        Dynamically check if a child question should be ignored based on the questions that have already been answered.

        :param: child:   The child question that might be ignored
        :param: answers: Answer values to previously asked questions
        """
        my_answer = answers.get(self.variablename)
        Abort.require_condition(
            my_answer is not None,
            "Questions were asked out of order. Please check your Application for consistency",
        )
        if my_answer is True:
            if child.variablename in self.whentrue_child_map:
                return False
            elif child.variablename in self.whenfalse_child_map:
                return True
            else:
                return False  # This child wasn't registered. This should not happen. But, don't ignore to be safe.
        else:
            if child.variablename in self.whentrue_child_map:
                return True
            elif child.variablename in self.whenfalse_child_map:
                return False
            else:
                return False  # This child wasn't registered. This should not happen. But, don't ignore to be safe.

    def make_ignore_partial(self, child: QuestionBase) -> Callable[[Dict[str, Any]], bool]:
        """
        Build a partial method for checking if a child should be ignored.

        This method just makes the code more readable so that a non-descriptive lambda does not need to be used inline.
        """
        return partial(self.ignore_child, child)

    def make_prompts(self, **override_kwargs):
        """
        Create ``inquirer`` prompts from this instance of ``BooleanList`` and for all its child questions.

        :param: override_kwargs: A collection of keyword arguments to override in the base ``make_prompts`` method
        """

        retval = super().make_prompts(**override_kwargs)
        all_children = [*self.whentrue_child_map.values(), *self.whenfalse_child_map.values()]
        for child in all_children:
            retval.extend(child.make_prompts(ignore=self.make_ignore_partial(child)))
        return retval


class Const(Text):
    """
    Sets the variable to the `default` value. Doesn't show anything.
    """

    def __init__(self, variablename: str, **kwargs):
        """
        Initialize the Const "question".

        :param: variablename:  The key in the config dictionary that this question will set
        """
        super().__init__(variablename, "", **kwargs)

    def make_prompts(self):
        """
        Create ``inquirer`` prompts from this instance of ``Const``.
        """
        return super().make_prompts(ignore=True)


def gather_param_values(
    application: JobbergateApplicationBase,
    supplied_params: Optional[Dict[str, Any]] = None,
    fast_mode: bool = False,
) -> Dict[str, Any]:
    """
    Gather the parameter values by executing the application methods.

    Prompt users for answers or use defaults as needed.

    :param: application:     The application instance to pull questions from
    :param: supplied_params: Pre-supplied parameters.
                             Any questions where the variablename matches a pre-supplied key in the dict
                             at the start of execution will be skipped.
    :param: fast_mode:       Do not ask the user questions. Just use the supplied params and defaults.
    :returns: A dict of the gathered parameter values
    """
    if supplied_params is None:
        supplied_params = dict()

    config = deepcopy(supplied_params)

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
                subject="Invalid application module",
            )

        prompts = []
        auto_answers = {}

        for question in workflow_questions:
            if question.variablename in supplied_params:
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

    return config
