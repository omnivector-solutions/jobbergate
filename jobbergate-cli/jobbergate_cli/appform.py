"""
Appform
=======
Abstraction layer for questions. Each class represents different question
types, and QuestionBase"""

from collections import deque
from functools import partial, wraps


questions = deque()
workflows = {}


class QuestionBase:
    """Baseclass for questions.
    All questions have variablename, message and an optional default.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    """

    def __init__(self, variablename, message, default):
        self.variablename = variablename
        self.message = message
        self.default = default


class Text(QuestionBase):
    """Asks for a text value.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    """

    def __init__(self, variablename, message, default=None):
        super().__init__(variablename, message, default)


class Integer(QuestionBase):
    """Asks for an integer value. Could have min and/or max constrains.
    :param variablename: The variable name to set
    :param message: Message to show
    :param minval: Minumum value
    :param maxval: Maximum value
    :param default: Default value
    """

    def __init__(self, variablename, message, minval=None, maxval=None, default=None):
        super().__init__(variablename, message, default)
        self.maxval = maxval
        self.minval = minval

    def validate(self, _, value):
        if self.minval is not None and self.maxval is not None:
            return self.minval <= int(value) <= self.maxval
        if self.minval is not None:
            return self.minval <= int(value)
        if self.maxval is not None:
            return int(value) <= self.maxval
        return True


class List(QuestionBase):
    """Gives the user a list to choose one from.
    :param variablename: The variable name to set
    :param message: Message to show
    :param choices: List with choices
    :param default: Default value"""

    def __init__(self, variablename, message, choices, default=None):
        super().__init__(variablename, message, default)
        self.choices = choices


class Directory(QuestionBase):
    """Asks for a directory name. If `exists` is `True` it checks if path exists and is a directory.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    :param exists: Checks if given directory exists"""

    def __init__(self, variablename, message, default=None, exists=None):
        super().__init__(variablename, message, default)
        self.exists = exists


class File(QuestionBase):
    """Asks for a file name. If `exists` is `True` it checks if path exists and is a directory.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    :param exists: Checks if given file exists"""

    def __init__(self, variablename, message, default=None, exists=None):
        super().__init__(variablename, message, default)
        self.exists = exists


class Checkbox(QuestionBase):
    """Gives the user a list to choose multiple entries from.
    :param variablename: The variable name to set
    :param message: Message to show
    :param choices: List with choices
    :param default: Default value(s)"""

    def __init__(self, variablename, message, choices, default=None):
        super().__init__(variablename, message, default)
        self.choices = choices


class Confirm(QuestionBase):
    """Asks a question with an boolean answer (true/false).
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    """

    def __init__(self, variablename, message, default=None):
        super().__init__(variablename, message, default)


class BooleanList(QuestionBase):
    """Gives the use a boolean question, and depending on answer it shows `whentrue` or `whenfalse` questions.
    `whentrue` and `whenfalse` are lists with questions. Could contain multiple levels of BooleanLists.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Default value
    :param whentrue: List of questions to show if user answers yes/true on this question
    :param whentrue: List of questions to show if user answers no/false on this question
    """

    def __init__(
        self, variablename, message, default=None, whentrue=None, whenfalse=None
    ):
        super().__init__(variablename, message, default)
        if whentrue is None and whenfalse is None:
            raise ValueError("Empty questions lists")
        self.whentrue = whentrue
        self.whenfalse = whenfalse
        self.ignore = lambda a: a[self.variablename]
        self.noignore = lambda a: not a[self.variablename]


class Const(QuestionBase):
    """Sets the variable to the `default` value. Doesn't show anything.
    :param variablename: The variable name to set
    :param message: Message to show
    :param default: Value that variable is set to
    """

    def __init__(self, variablename, default):
        super().__init__(variablename, None, default)


def workflow(func=None, *, name=None):
    """A decorator for workflows. Adds an workflow question and all questions
    added in the decorated question is asked after selecting workflow.
    :param name: (optional) Descriptional name that is shown when choosing workflow
    Add a workflow named debug:
    .. code-block:: python
        @workflow
        def debug(data):
            return [appform.File("debugfile", "Name of debug file")]
    Add a workflow with longer name:
    .. code-block:: python
        @workflow(name="Secondary Eigen step")
        def 2ndstep(data):
            return [appform.Text("eigendata", "Definition of eigendata")]
    """

    if func is None:
        return partial(workflow, name=name)

    @wraps(func)
    def wrapper(*args, **kvargs):
        return func(*args, **kvargs)

    workflows[name or func.__name__] = func

    return
