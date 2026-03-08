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


def test_text__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Text(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": "bar"}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == "bar"


def test_integer__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": 13}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == 13


def test_integer__zero_as_default():
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


def test_integer__fails_with_outside_of_range(dummy_render_class, mocker):
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!", minval=14, maxval=16)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": 13}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)

    dummy_render_class.prepared_input = {"foo": 17}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_list__success(dummy_render_class, mocker):
    variablename = "foo"
    question = List(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": "b"}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == "b"


def test_directory__success(tmp_path, dummy_render_class, mocker):
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": tmp_path}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == tmp_path


def test_directory__fails_if_directory_does_not_exist(dummy_render_class, mocker):
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": "not/a/real/path"}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_file__success(tmp_path, dummy_render_class, mocker):
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_file = tmp_path / "dummy"
    dummy_file.write_text("just some dome stuff")
    dummy_render_class.prepared_input = {"foo": dummy_file.as_posix()}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == dummy_file.as_posix()


def test_file__fails_if_file_does_not_exist(dummy_render_class, mocker):
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": "not/a/real/path"}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    with pytest.raises(ValidationError):
        prompt(prompts)


def test_checkbox__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Checkbox(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": ["a", "b"]}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] == ["a", "b"]


def test_confirm__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Confirm(variablename, "gimme the foo?")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {"foo": True}

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = prompt(prompts)
    assert answers["foo"] is True


def test_const__success(dummy_render_class, mocker):
    variablename = "foo"
    question = Const(variablename, default="bar")
    prompts = question.make_prompts()

    dummy_render_class.prepared_input = {}

    answers = prompt(prompts, render=dummy_render_class())
    assert answers["foo"] == "bar"


def test_boolean_list__success(dummy_render_class, mocker):
    variablename_tt1 = "fooTT1"
    question_tt1 = Confirm(variablename_tt1, message="gimme the fooTT1!", default=False)

    variablename_t1 = "fooT1"
    question_t1 = BooleanList(variablename_t1, message="gimme the fooT1!", whentrue=[question_tt1], default=False)

    variablename_t2 = "fooT2"
    question_t2 = Confirm(variablename_t2, message="gimme the fooT2!", default=False)

    variablename_ff1 = "fooFF1"
    question_ff1 = Confirm(variablename_ff1, message="gimme the fooFF1!", default=False)

    variablename_f1 = "fooF1"
    question_f1 = BooleanList(variablename_f1, message="gimme the fooF1!", whentrue=[question_ff1], default=False)

    variablename = "foo"
    question = BooleanList(
        variablename,
        message="gimme the foo1!",
        whentrue=[question_t1, question_t2],
        whenfalse=[question_f1],
        default=False,
    )

    prompts = question.make_prompts()

    # We'll answer True to any questions asked to make sure we are ignoring the correct ones
    dummy_render_class.prepared_input = {
        "fooTT1": True,
        "fooT1": True,
        "fooT2": True,
        "fooFF1": True,
        "fooF1": True,
        "foo": True,
    }

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    answers = {}
    answers = prompt(prompts, answers=answers, render=dummy_render_class())

    # Only ignored questions should be false
    assert answers == {
        "fooTT1": True,
        "fooT1": True,
        "fooT2": True,
        "fooFF1": False,
        "fooF1": False,
        "foo": True,
    }


@pytest.mark.parametrize("parent_answer", [True, False])
def test_boolean_list__same_variable_name(dummy_render_class, parent_answer):
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
