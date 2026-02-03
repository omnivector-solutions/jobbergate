"""
Textual-based TUI prompt implementation for jobbergate-cli.

Provides an interactive terminal UI for gathering application parameters
with real-time validation and visual feedback.
"""

from __future__ import annotations

import pathlib
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.validation import ValidationResult, Validator
from textual.widgets import Button, Checkbox, Input, Label, Select, Switch

from jobbergate_cli.subapps.applications.prompts import PromptABC
from jobbergate_cli.subapps.applications.questions import (
    BooleanList,
    Checkbox as CheckboxQuestion,
    Confirm,
    Const,
    Directory,
    File,
    Integer,
    List as ListQuestion,
    QuestionBase,
    Text,
)


class IntegerValidator(Validator):
    """Validator for integer inputs with optional min/max constraints."""

    def __init__(self, minval: int | None = None, maxval: int | None = None) -> None:
        super().__init__()
        self.minval = minval
        self.maxval = maxval

    def validate(self, value: str) -> ValidationResult:
        """Validate that the value is an integer within the specified range."""
        if not value:
            return self.failure("Value cannot be empty")

        try:
            int_val = int(value)
        except ValueError:
            return self.failure(f"{value} is not an integer")

        min_str = str(self.minval) if self.minval is not None else "-∞"
        max_str = str(self.maxval) if self.maxval is not None else "∞"

        if self.minval is not None and int_val < self.minval:
            return self.failure(f"{value} is out of range [{min_str}, {max_str}]")
        if self.maxval is not None and int_val > self.maxval:
            return self.failure(f"{value} is out of range [{min_str}, {max_str}]")

        return self.success()


class PathValidator(Validator):
    """Validator for file/directory paths with optional existence checks."""

    def __init__(self, path_type: str = "file", exists: bool | None = None) -> None:
        super().__init__()
        self.path_type = path_type
        self.exists = exists

    def validate(self, value: str) -> ValidationResult:
        """Validate that the path exists and is of the correct type if required."""
        if not value:
            return self.failure("Path cannot be empty")

        if self.exists is None:
            return self.success()

        path = pathlib.Path(value).expanduser()

        if self.exists:
            if not path.exists():
                return self.failure(f"Path does not exist: {value}")
            if self.path_type == "directory" and not path.is_dir():
                return self.failure(f"Path is not a directory: {value}")
            elif self.path_type == "file" and not path.is_file():
                return self.failure(f"Path is not a file: {value}")

        return self.success()


class ErrorModal(ModalScreen[None]):
    """Modal screen to display validation errors."""

    DEFAULT_CSS = """
    ErrorModal {
        align: center middle;
    }

    #error-dialog {
        width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #error-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
    }

    #error-message {
        width: 100%;
        margin: 1 0;
    }

    #error-button-container {
        width: 100%;
        height: auto;
        align: center middle;
    }
    """

    def __init__(self, errors: list[str]) -> None:
        super().__init__()
        self.errors = errors

    def compose(self) -> ComposeResult:
        """Compose the error modal."""
        with Container(id="error-dialog"):
            yield Label("Validation Errors", id="error-title")
            for error in self.errors:
                yield Label(f"• {error}", id="error-message")
            with Horizontal(id="error-button-container"):
                yield Button("OK", variant="error", id="ok-button")

    @on(Button.Pressed, "#ok-button")
    def dismiss_modal(self) -> None:
        """Dismiss the error modal."""
        self.app.pop_screen()


class QuestionScreen(Screen[dict[str, Any]]):
    """Screen to display a group of questions."""

    DEFAULT_CSS = """
    QuestionScreen {
        align: center middle;
    }

    #question-container {
        width: 80;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }

    #question-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .question-label {
        margin-top: 1;
        margin-bottom: 0;
    }

    .question-input {
        margin-bottom: 1;
    }

    Input.-valid {
        border: tall $success;
    }

    Input.-invalid {
        border: tall $error;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    #button-container Horizontal {
        width: auto;
        height: auto;
    }
    """

    def __init__(self, questions: list[QuestionBase], workflow_name: str = "Questions") -> None:
        super().__init__()
        self.questions = questions
        self.workflow_name = workflow_name
        self.answers: dict[str, Any] = {}
        self.widgets_map: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the question screen."""
        with Vertical(id="question-container"):
            yield Label(self.workflow_name, id="question-title")

            for question in self.questions:
                if isinstance(question, Const):
                    # Skip Const questions as they are hidden
                    self.answers[question.variablename] = question.default
                    continue

                yield Label(question.inquirer_kwargs.get("message", ""), classes="question-label")

                widget = self._create_widget_for_question(question)
                if widget:
                    yield widget

            with Horizontal(id="button-container"):
                yield Button("Continue", variant="success", id="continue-button")
                yield Button("Cancel", variant="error", id="cancel-button")
    
    def on_mount(self) -> None:
        """Validate all inputs on mount to show initial validation state."""
        for variablename, widget in self.widgets_map.items():
            if isinstance(widget, Input) and widget.value:
                # Trigger validation for inputs with default values
                validation_result = widget.validate(widget.value)
                if validation_result and validation_result.is_valid:
                    widget.add_class("-valid")
                elif validation_result and not validation_result.is_valid:
                    widget.add_class("-invalid")

    def _create_widget_for_question(self, question: QuestionBase) -> Any:
        """Create the appropriate widget for a question type."""
        if isinstance(question, Integer):
            widget = Input(
                placeholder=str(question.default) if question.default is not None else "",
                value=str(question.default) if question.default not in (None, "") else "",
                validators=[IntegerValidator(question.minval, question.maxval)],
                id=f"input-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        elif isinstance(question, Text):
            widget = Input(
                placeholder=str(question.default) if question.default is not None else "",
                value=str(question.default) if question.default is not None else "",
                id=f"input-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        elif isinstance(question, Directory):
            widget = Input(
                placeholder=str(question.default) if question.default is not None else "",
                value=str(question.default) if question.default is not None else "",
                validators=[PathValidator("directory", question.inquirer_kwargs.get("exists"))],
                id=f"input-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        elif isinstance(question, File):
            widget = Input(
                placeholder=str(question.default) if question.default is not None else "",
                value=str(question.default) if question.default is not None else "",
                validators=[PathValidator("file", question.inquirer_kwargs.get("exists"))],
                id=f"input-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        elif isinstance(question, ListQuestion):
            choices = question.inquirer_kwargs.get("choices", [])
            options = [(str(choice), str(choice)) for choice in choices]
            widget = Select(
                options=options,
                value=question.default if question.default is not None else None,
                id=f"select-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        elif isinstance(question, CheckboxQuestion):
            choices = question.inquirer_kwargs.get("choices", [])
            container = Vertical(id=f"checkbox-{question.variablename}", classes="question-input")
            self.widgets_map[question.variablename] = []

            for choice in choices:
                checkbox = Checkbox(
                    str(choice),
                    value=question.default and choice in question.default if question.default else False,
                    id=f"checkbox-{question.variablename}-{choice}",
                )
                self.widgets_map[question.variablename].append((choice, checkbox))
                container.compose_add_child(checkbox)

            return container

        elif isinstance(question, (Confirm, BooleanList)):
            widget = Switch(
                value=question.default if question.default is not None else False,
                id=f"switch-{question.variablename}",
                classes="question-input",
            )
            self.widgets_map[question.variablename] = widget
            return widget

        return None

    @on(Input.Changed)
    def validate_input(self, event: Input.Changed) -> None:
        """Validate input fields in real-time and update styling."""
        if event.validation_result and event.validation_result.is_valid:
            event.input.remove_class("-invalid")
            event.input.add_class("-valid")
        else:
            event.input.remove_class("-valid")
            event.input.add_class("-invalid")

    @on(Button.Pressed, "#continue-button")
    def handle_continue(self) -> None:
        """Handle continue button press."""
        errors = []

        # Validate all inputs and gather answers
        for question in self.questions:
            if isinstance(question, Const):
                continue

            variablename = question.variablename
            widget = self.widgets_map.get(variablename)

            if widget is None:
                continue

            if isinstance(widget, Input):
                # Validate input (only if validators are present)
                if widget.validators:
                    validation_result = widget.validate(widget.value)
                    if validation_result and not validation_result.is_valid:
                        errors.append(f"{question.inquirer_kwargs.get('message', variablename)}: {validation_result.failure_descriptions[0] if validation_result.failure_descriptions else 'Invalid value'}")
                        continue
                
                # Store the answer
                if isinstance(question, Integer):
                    self.answers[variablename] = int(widget.value) if widget.value else question.default
                else:
                    self.answers[variablename] = widget.value or question.default

            elif isinstance(widget, Select):
                self.answers[variablename] = widget.value

            elif isinstance(widget, Switch):
                self.answers[variablename] = widget.value

            elif isinstance(widget, list):
                # Checkbox question
                selected = [choice for choice, checkbox in widget if checkbox.value]
                self.answers[variablename] = selected

        if errors:
            self.app.push_screen(ErrorModal(errors))
        else:
            self.dismiss(self.answers)

    @on(Button.Pressed, "#cancel-button")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        # Set cancelled flag and exit with empty result
        self.app.cancelled = True
        self.app.exit({})


class TextualPromptApp(App[dict[str, Any]]):
    """Textual application for prompting questions."""

    CSS = """
    Screen {
        background: $background;
    }
    """

    def __init__(self, questions: list[QuestionBase], workflow_name: str = "Questions") -> None:
        super().__init__()
        self.questions = questions
        self.workflow_name = workflow_name
        self.result: dict[str, Any] = {}
        self.cancelled = False
        self.error: Exception | None = None

    def on_mount(self) -> None:
        """Show the question screen on mount."""
        self.push_screen(QuestionScreen(self.questions, self.workflow_name), self._handle_result)

    def _handle_result(self, answers: dict[str, Any]) -> None:
        """Handle the result from the question screen."""
        self.result = answers
        self.exit(answers)


class TextualPrompt(PromptABC):
    """Textual-based prompt implementation."""
    
    def needs_raw_questions(self) -> bool:
        """TextualPrompt needs raw QuestionBase objects, not inquirer prompts."""
        return True

    def run(self, questions: list[QuestionBase]) -> dict[str, Any]:
        """
        Run the Textual TUI to gather answers to questions.

        Args:
            questions: List of QuestionBase questions to ask the user.

        Returns:
            Dictionary of answers keyed by variable name.
            
        Raises:
            Abort: If the user cancels the operation.
        """
        from jobbergate_cli.exceptions import Abort
        
        if not questions:
            return {}

        app = TextualPromptApp(questions, workflow_name="Application Questions")
        result = app.run()
        
        # Check if user cancelled
        if app.cancelled:
            raise Abort("User cancelled the operation", subject="Operation cancelled")

        return result or {}
