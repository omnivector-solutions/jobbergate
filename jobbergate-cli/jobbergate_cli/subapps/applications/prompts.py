from abc import ABC
from typing import Any
import inquirer
from jobbergate_cli.subapps.applications.questions import QuestionBase


class PromptABC(ABC):
    """Abstract base class for prompt strategies."""
    
    def run(self, questions: list[QuestionBase]) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method.")
    
    def needs_raw_questions(self) -> bool:
        """Return True if the prompt strategy needs raw QuestionBase objects instead of inquirer prompts."""
        return False


class InquirerPrompt(PromptABC):
    def run(self, questions: list[QuestionBase]) -> dict[str, Any]:
        return inquirer.prompt(questions, raise_keyboard_interrupt=True) or {}
