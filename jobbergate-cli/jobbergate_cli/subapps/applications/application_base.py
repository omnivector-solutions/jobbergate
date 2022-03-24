"""ApplicationBase."""

import pathlib
from typing import Any, Dict, List

from jobbergate_cli.render import terminal_message
from jobbergate_cli.text_tools import dedent_all


class JobbergateApplicationBase:
    """JobbergateApplicationBase."""

    def __init__(self, jobbergate_yaml: Dict[str, Any]):
        """Initialize class attributes."""
        self.jobbergate_config = jobbergate_yaml["jobbergate_config"]
        self.application_config = jobbergate_yaml.get("application_config", dict())

    def mainflow(self, data: Dict[str, Any]):
        """Implements the main question asking workflow."""
        data  # Makes linters happy
        raise NotImplementedError("Inheriting class must override this method.")

    @staticmethod
    def find_templates(application_path: pathlib.Path) -> List[pathlib.Path]:
        """
        Finds templates a given application path.
        """
        template_root_path = application_path / "templates"
        if template_root_path.exists():
            return sorted(p.relative_to(application_path) for p in template_root_path.glob("**/*") if p.is_file())
        else:
            return list()

    def get_template_files(self) -> List[pathlib.Path]:
        template_file_paths = self.find_templates(pathlib.Path.cwd())
        terminal_message(
            dedent_all(
                f"""
                Here are all of the included templates:
                [yellow](in {pathlib.Path.cwd()})[/yellow]
                ---------------------------------------
                """,
                *(f"* {p}" for p in template_file_paths),
            ),
            subject="Template Files",
            color="green",
        )
        return template_file_paths
