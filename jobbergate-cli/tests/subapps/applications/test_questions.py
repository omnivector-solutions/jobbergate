import typing
from unittest import mock

import inquirer.prompt

from jobbergate_cli.subapps.applications.questions import Text


class DummyRender:
    prepared_input: typing.Dict[str, typing.Any]

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def render(self, question):
        if question.ignore:
            return question.default
        question.answers = self.prepared_input[question.variable_name]



def test_Text_question():
    print("TYPE: ", inquirer.prompt)

    variable_name = "foo"
    question = Text(variable_name, "gimme the foo!")
    prompts = question.make_prompts()

    DummyRender.prepared_input = dict(foo="bar")

    with mock.patch("inquirer.prompt.ConsoleRender", new=DummyRender):
        answers = inquirer.prompt.prompt(prompts)
        assert answers["foo"] == "bar"
