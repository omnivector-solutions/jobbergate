import importlib
from unittest import mock

import pytest
from inquirer import prompt
from inquirer.errors import ValidationError

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.subapps.applications.questions import (
    Text,
    Integer,
    List,
    Directory,
    File,
    Checkbox,
    Confirm,
    BooleanList,
    Const,
    gather_config_values,
)

from tests.subapps.applications.conftest import DummyRender


def test_Text__success():
    variablename = "foo"
    question = Text(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo="bar")

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == "bar"


def test_Integer__success():
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!")
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo=13)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == 13


def test_Integer__fails_with_outside_of_range():
    variablename = "foo"
    question = Integer(variablename, "gimme the foo!", minval=14, maxval=16)
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo=13)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        with pytest.raises(ValidationError):
            prompt(prompts)

    DummyRender.prepared_input = dict(foo=17)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        with pytest.raises(ValidationError):
            prompt(prompts)


def test_List__success():
    variablename = "foo"
    question = List(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo="b")

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == "b"


def test_Directory__success(tmp_path):
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo=tmp_path)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == tmp_path


def test_Directory__fails_if_directory_does_not_exist():
    variablename = "foo"
    question = Directory(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo="not/a/real/path")

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        with pytest.raises(ValidationError):
            prompt(prompts)


def test_File__success(tmp_path):
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    dummy_file = tmp_path / "dummy"
    dummy_file.write_text("just some dome stuff")
    DummyRender.prepared_input = dict(foo=dummy_file)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == dummy_file


def test_File__fails_if_file_does_not_exist():
    variablename = "foo"
    question = File(variablename, "gimme the foo!", exists=True)
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo="not/a/real/path")

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        with pytest.raises(ValidationError):
            prompt(prompts)


def test_Checkbox__success():
    variablename = "foo"
    question = Checkbox(variablename, "gimme the foo!", ["a", "b", "c"])
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo=["a", "b"])

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == ["a", "b"]


def test_Confirm__success():
    variablename = "foo"
    question = Confirm(variablename, "gimme the foo?")
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo=True)

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == True


def test_Const__success():
    variablename = "foo"
    question = Const(variablename, default="bar")
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict()

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert answers["foo"] == "bar"


@pytest.mark.xfail(reason="Need to understand this method better before I can finish the test")
def test_BooleanList__success():
    variablenameTT1 = "fooTT1"
    questionTT1 = Confirm(variablenameTT1, message="gimme the fooTT1!")

    variablenameT1 = "fooT1"
    questionT1 = BooleanList(variablenameT1, message="gimme the fooT1!", whentrue=[questionTT1])

    variablenameT2 = "fooT2"
    questionT2 = Confirm(variablenameT2, message="gimme the fooT2!")

    variablenameFF1 = "fooFF1"
    questionFF1 = Confirm(variablenameFF1, message="gimme the fooFF1!")

    variablenameF1 = "fooF1"
    questionF1 = BooleanList(variablenameF1, message="gimme the fooF1!", whenfalse=[questionFF1])

    variablename = "foo"
    question = BooleanList(
        variablename,
        message="gimme the foo1!",
        whentrue=[questionT1, questionT2],
        whenfalse=[questionF1],
    )

    prompts = question.make_prompts()
    print("PROMPTS: ", prompts)

    DummyRender.prepared_input = dict(
        fooTT1=True,
        fooT1=True,
        fooT2=True,
        fooFF1=True,
        fooF1=True,
        foo=True,
    )

    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        answers = prompt(prompts)
        assert False


def test_gather_config_values__basic():
    variablename1 = "foo"
    question1 = Text(variablename1, message="gimme the foo!")

    variablename2 = "bar"
    question2 = Text(variablename2, message="gimme the bar!")

    variablename3 = "baz"
    question3 = Text(variablename3, message="gimme the baz!")

    class DummyApplication:
        def mainflow(self, data):
            data["nextworkflow"] = "subflow"
            return [question1, question2]

        def subflow(self, data):
            return [question3]



    DummyRender.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    config = dict()
    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        gather_config_values(DummyApplication(), config)
        assert config == dict(
            foo="FOO",
            bar="BAR",
            baz="BAZ",
        )


def test_gather_config_values__fast_mode():
    variablename1 = "foo"
    question1 = Text(variablename1, message="gimme the foo!", default="oof")

    variablename2 = "bar"
    question2 = Text(variablename2, message="gimme the bar!")

    variablename3 = "baz"
    question3 = Text(variablename3, message="gimme the baz!")

    class DummyApplication:
        def mainflow(self, data):
            data["nextworkflow"] = "subflow"
            return [question1, question2]

        def subflow(self, data):
            return [question3]



    DummyRender.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    config = dict()
    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        gather_config_values(DummyApplication(), config, fast_mode=True)
        assert config == dict(
            foo="oof",
            bar="BAR",
            baz="BAZ",
        )


def test_gather_config_values__with_supplied_params():
    variablename1 = "foo"
    question1 = Text(variablename1, message="gimme the foo!", default="oof")

    variablename2 = "bar"
    question2 = Text(variablename2, message="gimme the bar!")

    variablename3 = "baz"
    question3 = Text(variablename3, message="gimme the baz!")

    class DummyApplication:
        def mainflow(self, data):
            data["nextworkflow"] = "subflow"
            return [question1, question2]

        def subflow(self, data):
            return [question3]



    DummyRender.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    config = dict()
    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        gather_config_values(DummyApplication(), config, supplied_params=dict(bar="rab"))
        assert config == dict(
            foo="FOO",
            bar="rab",
            baz="BAZ",
        )


def test_gather_config_values__raises_Abort_if_method_not_implemented():
    variablename1 = "foo"
    question1 = Text(variablename1, message="gimme the foo!")

    class DummyApplication:
        def mainflow(self, data):
            data["nextworkflow"] = "subflow"
            return [question1]

        def subflow(self, data):
            raise NotImplementedError("BOOM!")


    DummyRender.prepared_input = dict(
        foo="FOO",
    )

    config = dict()
    with mock.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=DummyRender):
        with pytest.raises(Abort, match="not implemented"):
            gather_config_values(DummyApplication(), config)
