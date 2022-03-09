"""ApplicationBase."""

import pathlib
from typing import Any, Dict, List

import snick

from jobbergate_cli.render import terminal_message
from jobbergate_cli.subapps.applications.tools import find_templates


class JobbergateApplicationBase:
    """JobbergateApplicationBase."""

    def __init__(self, jobbergate_yaml: Dict[str, Any]):
        """Initialize class attributes."""
        self.jobbergate_config = jobbergate_yaml["jobbergate_config"]
        self.application_config = jobbergate_yaml["application_config"]

    def mainflow(self, data: Dict[str, Any]):
        """Implements the main question asking workflow."""
        data  # Makes linters happy
        raise NotImplementedError("Inheriting class must override this method.")

    def get_template_files(self) -> List[pathlib.Path]:
        template_file_paths = find_templates(pathlib.Path.cwd())
        terminal_message(
            snick.dedent_all(
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
