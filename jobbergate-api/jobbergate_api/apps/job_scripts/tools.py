"""Provide a convenience class for managing job-script files."""

from typing import Any

from jinja2 import Template
from loguru import logger

from jobbergate_api.apps.models import Base
from jobbergate_api.apps.services import FileService


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: list[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    logger.debug("Preparing to inject sbatch params into job script")

    if not sbatch_params:
        logger.warning("Sbatch param list is empty")
        return job_script_data_as_string

    first_sbatch_index = job_script_data_as_string.find("#SBATCH")
    string_slice = job_script_data_as_string[first_sbatch_index:]
    line_end = string_slice.find("\n") + first_sbatch_index + 1

    inner_string = ""
    for parameter in sbatch_params:
        inner_string += "#SBATCH " + parameter + "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:line_end] + inner_string + job_script_data_as_string[line_end:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


async def render_template_file(
    file_service: FileService, template_file: Base, parameters: dict[str, Any]
) -> str:
    """Render a Jinja2 template."""
    file_content = await file_service.get(template_file)
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8")
    return Template(file_content).render(**parameters)
