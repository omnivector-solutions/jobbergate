import importlib

import pytest
from inquirer import prompt
from inquirer.errors import ValidationError

from jobbergate_cli.subapps.applications.questions import (
    BooleanList,
    Checkbox,
    Confirm,
    Const,
    Directory,
    File,
    Integer,
    List,
    Text,
)


def test_Text__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Text(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo="bar")

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == "bar"


def test_Integer__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo=13)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == 13


def test_Integer__zero_as_default():
    """
    The default of zero is an eddy case for inquired.

    Due to implementation details on inquire and the fact that its boolean equivalent
    is false, `0` was not set as default and was not presented on the questions.

    We need to ensure it is.
    """
    question = Integer("foo", "gimme the foo!", default=0)
    prompts = question.make_prompts()

    prompt = prompts.pop()

    assert bool(prompt.default) is True
    assert int(prompt.default) == 0


def test_Integer__fails_with_outside_of_range(dummy_render_class, mocker):
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!", minval=14, maxval=16)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo=13)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)

    dummy_render_class.prepared_input = dict(foo=17)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_List__success(dummy_render_class, mocker):
    variablename = "foo"
    question = List(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo="b")

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == "b"


def test_Directory__success(tmp_path, dummy_render_class, mocker):
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo=tmp_path)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == tmp_path


def test_Directory__fails_if_directory_does_not_exist(dummy_render_class, mocker):
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo="not/a/real/path")

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_File__success(tmp_path, dummy_render_class, mocker):
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_file = tmp_path / "dummy"
    dummy_file.write_text("just some dome stuff")
    dummy_render_class.prepared_input = dict(foo=dummy_file)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == dummy_file


def test_File__fails_if_file_does_not_exist(dummy_render_class, mocker):
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo="not/a/real/path")

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_Checkbox__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Checkbox(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo=["a", "b"])

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == ["a", "b"]


def test_Confirm__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Confirm(variablename, "gimme the foo?")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict(foo=True)

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] is True


def test_Const__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Const(variablename, default="bar")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = dict()

    answers = prompt(prompts, render=dummy_render_class())
    assert answers["foo"] == "bar"


def test_BooleanList__success(dummy_render_class, mocker):
    variablenameTT1 = "fooTT1"
    questionTT1 = Confirm(variablenameTT1, message="gimme the fooTT1!", default=False)

    variablenameT1 = "fooT1"
    questionT1 = BooleanList(variablenameT1, message="gimme the fooT1!", whentrue=[questionTT1], default=False)

    variablenameT2 = "fooT2"
    questionT2 = Confirm(variablenameT2, message="gimme the fooT2!", default=False)

    variablenameFF1 = "fooFF1"
    questionFF1 = Confirm(variablenameFF1, message="gimme the fooFF1!", default=False)

    variablenameF1 = "fooF1"
    questionF1 = BooleanList(variablenameF1, message="gimme the fooF1!", whentrue=[questionFF1], default=False)

    variablename = "foo"
    question = BooleanList(
        variablename,
        message="gimme the foo1!",
        whentrue=[questionT1, questionT2],
        whenfalse=[questionF1],
        default=False,
    )

    prompts = question.make_prompts()

    # We'll answer True to any questions asked to make sure we are ignoring the correct ones
    dummy_render_class.prepared_input = dict(
        fooTT1=True,
        fooT1=True,
        fooT2=True,
        fooFF1=True,
        fooF1=True,
        foo=True,
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = dict()
    answers = prompt(prompts, answers=answers, render=dummy_render_class())

    # Only ignored questions should be false
    assert answers == dict(
        fooTT1=True,
        fooT1=True,
        fooT2=True,
        fooFF1=False,
        fooF1=False,
        foo=True,
    )


@pytest.mark.parametrize("parent_answer", [True, False])
def test_BooleanList__same_variable_name(dummy_render_class, parent_answer):
    """Assert that BooleanList works when multiple children have the same variable name."""
    variablename = "child"
    question_a = Text(variablename, message="Question A")
    question_b = Text(variablename, message="Question B")

    question = BooleanList("parent", message="Parent", whentrue=[question_a], whenfalse=[question_b], default=False)
    prompts = question.make_prompts()

    expected_answers = {"parent": parent_answer, variablename: "any-answer"}
    dummy_render_class.prepared_input = expected_answers

    actual_answers = prompt(prompts, answers=expected_answers, render=dummy_render_class())
    assert actual_answers == expected_answers

    expected_ignored_questions = [False, not parent_answer, parent_answer]
    actual_ignored_questions = [q.ignore for q in prompts]
    assert actual_ignored_questions == expected_ignored_questions
