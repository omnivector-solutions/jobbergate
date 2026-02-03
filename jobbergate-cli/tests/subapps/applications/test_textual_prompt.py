"""
Unit tests for the TextualPrompt implementation.
"""

import pytest
from unittest.mock import MagicMock, patch

from jobbergate_cli.subapps.applications.textual_prompt import (
    IntegerValidator,
    PathValidator,
    TextualPrompt,
    TextualPromptApp,
)
from jobbergate_cli.subapps.applications.questions import (
    Checkbox,
    Confirm,
    Const,
    Directory,
    File,
    Integer,
    List,
    Text,
)


class TestIntegerValidator:
    """Tests for the IntegerValidator class."""

    def test_validate_empty_value(self):
        """Test that empty values are rejected."""
        validator = IntegerValidator()
        result = validator.validate("")
        assert not result.is_valid
        assert "Value cannot be empty" in result.failure_descriptions[0]

    def test_validate_non_integer(self):
        """Test that non-integer values are rejected."""
        validator = IntegerValidator()
        result = validator.validate("abc")
        assert not result.is_valid
        assert "is not an integer" in result.failure_descriptions[0]

    def test_validate_valid_integer(self):
        """Test that valid integers are accepted."""
        validator = IntegerValidator()
        result = validator.validate("42")
        assert result.is_valid

    def test_validate_below_minimum(self):
        """Test that values below minimum are rejected."""
        validator = IntegerValidator(minval=10, maxval=100)
        result = validator.validate("5")
        assert not result.is_valid
        assert "out of range" in result.failure_descriptions[0]

    def test_validate_above_maximum(self):
        """Test that values above maximum are rejected."""
        validator = IntegerValidator(minval=10, maxval=100)
        result = validator.validate("150")
        assert not result.is_valid
        assert "out of range" in result.failure_descriptions[0]

    def test_validate_within_range(self):
        """Test that values within range are accepted."""
        validator = IntegerValidator(minval=10, maxval=100)
        result = validator.validate("50")
        assert result.is_valid


class TestPathValidator:
    """Tests for the PathValidator class."""

    def test_validate_empty_path(self):
        """Test that empty paths are rejected."""
        validator = PathValidator()
        result = validator.validate("")
        assert not result.is_valid
        assert "Path cannot be empty" in result.failure_descriptions[0]

    def test_validate_path_no_existence_check(self):
        """Test that paths are accepted when existence check is disabled."""
        validator = PathValidator(exists=None)
        result = validator.validate("/some/path")
        assert result.is_valid

    def test_validate_nonexistent_file(self, tmp_path):
        """Test that nonexistent files are rejected when exists=True."""
        validator = PathValidator(path_type="file", exists=True)
        result = validator.validate(str(tmp_path / "nonexistent.txt"))
        assert not result.is_valid
        assert "does not exist" in result.failure_descriptions[0]

    def test_validate_existing_file(self, tmp_path):
        """Test that existing files are accepted when exists=True."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        validator = PathValidator(path_type="file", exists=True)
        result = validator.validate(str(test_file))
        assert result.is_valid

    def test_validate_directory_as_file(self, tmp_path):
        """Test that directories are rejected when expecting a file."""
        validator = PathValidator(path_type="file", exists=True)
        result = validator.validate(str(tmp_path))
        assert not result.is_valid
        assert "is not a file" in result.failure_descriptions[0]

    def test_validate_file_as_directory(self, tmp_path):
        """Test that files are rejected when expecting a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        validator = PathValidator(path_type="directory", exists=True)
        result = validator.validate(str(test_file))
        assert not result.is_valid
        assert "is not a directory" in result.failure_descriptions[0]

    def test_validate_existing_directory(self, tmp_path):
        """Test that existing directories are accepted when exists=True."""
        validator = PathValidator(path_type="directory", exists=True)
        result = validator.validate(str(tmp_path))
        assert result.is_valid


class TestTextualPrompt:
    """Tests for the TextualPrompt class."""

    def test_run_with_empty_questions(self):
        """Test that running with no questions returns empty dict."""
        prompt = TextualPrompt()
        result = prompt.run([])
        assert result == {}

    @patch("jobbergate_cli.subapps.applications.textual_prompt.TextualPromptApp")
    def test_run_with_questions(self, mock_app_class):
        """Test that run creates and runs the TextualPromptApp."""
        mock_app = MagicMock()
        mock_app.run.return_value = {"var1": "value1"}
        mock_app.cancelled = False  # User did not cancel
        mock_app_class.return_value = mock_app

        questions = [
            Text("var1", "Question 1", default="default1"),
        ]

        prompt = TextualPrompt()
        result = prompt.run(questions)

        # Verify app was created with questions
        mock_app_class.assert_called_once_with(questions, workflow_name="Application Questions")

        # Verify app.run was called
        mock_app.run.assert_called_once()

        # Verify result
        assert result == {"var1": "value1"}

    @patch("jobbergate_cli.subapps.applications.textual_prompt.TextualPromptApp")
    def test_run_with_none_result(self, mock_app_class):
        """Test that run handles None result from app."""
        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_app.cancelled = False  # User did not cancel
        mock_app_class.return_value = mock_app

        questions = [Text("var1", "Question 1")]

        prompt = TextualPrompt()
        result = prompt.run(questions)

        assert result == {}

    @patch("jobbergate_cli.subapps.applications.textual_prompt.TextualPromptApp")
    def test_run_with_user_cancel(self, mock_app_class):
        """Test that run raises Abort when user cancels."""
        from jobbergate_cli.exceptions import Abort
        
        mock_app = MagicMock()
        mock_app.run.return_value = {}
        mock_app.cancelled = True  # User cancelled
        mock_app_class.return_value = mock_app

        questions = [Text("var1", "Question 1")]

        prompt = TextualPrompt()
        
        with pytest.raises(Abort) as exc_info:
            prompt.run(questions)
        
        assert "cancelled" in str(exc_info.value).lower()


class TestTextualPromptApp:
    """Tests for the TextualPromptApp class."""

    def test_app_initialization(self):
        """Test that the app initializes with questions."""
        questions = [
            Text("var1", "Question 1", default="default1"),
            Integer("var2", "Question 2", minval=1, maxval=10, default=5),
        ]

        app = TextualPromptApp(questions, workflow_name="Test Workflow")

        assert app.questions == questions
        assert app.workflow_name == "Test Workflow"
        assert app.result == {}


class TestQuestionWidgetMapping:
    """Tests for question widget mapping logic."""

    @pytest.mark.skip(reason="Requires active Textual app context")
    def test_text_question_widget_type(self):
        """Test that Text questions create Input widgets."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Input

        questions = [Text("name", "Enter your name", default="John")]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        # Just verify widget type, not value (which requires active app)
        assert widget is not None
        assert isinstance(widget, Input)

    @pytest.mark.skip(reason="Requires active Textual app context")
    def test_integer_question_creates_input_with_validator(self):
        """Test that Integer questions create Input with IntegerValidator."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Input

        questions = [Integer("age", "Enter your age", minval=0, maxval=120, default=25)]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        assert widget is not None
        assert isinstance(widget, Input)
        assert hasattr(widget, "validators")
        assert len(widget.validators) == 1
        assert isinstance(widget.validators[0], IntegerValidator)

    def test_list_question_widget_type(self):
        """Test that List questions create Select widgets."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Select

        questions = [List("choice", "Select an option", choices=["A", "B", "C"], default="B")]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        # Just verify widget type
        assert widget is not None
        assert isinstance(widget, Select)

    def test_checkbox_question_creates_container(self):
        """Test that Checkbox questions create a container."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.containers import Vertical

        questions = [Checkbox("multi", "Select multiple", choices=["X", "Y", "Z"], default=["X"])]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        assert widget is not None
        assert isinstance(widget, Vertical)

    def test_confirm_question_widget_type(self):
        """Test that Confirm questions create Switch widgets."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Switch

        questions = [Confirm("agree", "Do you agree?", default=True)]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        assert widget is not None
        assert isinstance(widget, Switch)

    @pytest.mark.skip(reason="Requires active Textual app context")
    def test_directory_question_creates_input_with_path_validator(self):
        """Test that Directory questions create Input with PathValidator."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Input

        questions = [Directory("dir", "Select directory", exists=True, default="/tmp")]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        assert widget is not None
        assert isinstance(widget, Input)
        assert hasattr(widget, "validators")
        assert len(widget.validators) == 1
        assert isinstance(widget.validators[0], PathValidator)

    @pytest.mark.skip(reason="Requires active Textual app context")
    def test_file_question_creates_input_with_path_validator(self):
        """Test that File questions create Input with PathValidator."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen
        from textual.widgets import Input

        questions = [File("file", "Select file", exists=True, default="/tmp/test.txt")]
        screen = QuestionScreen(questions)

        widget = screen._create_widget_for_question(questions[0])

        assert widget is not None
        assert isinstance(widget, Input)
        assert hasattr(widget, "validators")
        assert len(widget.validators) == 1
        assert isinstance(widget.validators[0], PathValidator)

    def test_const_question_is_skipped(self):
        """Test that Const questions are skipped in widget creation."""
        from jobbergate_cli.subapps.applications.textual_prompt import QuestionScreen

        questions = [Const("hidden", default="secret_value")]
        screen = QuestionScreen(questions)

        # Const questions should be added directly to answers
        assert "hidden" not in screen.widgets_map
