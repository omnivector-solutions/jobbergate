"""Provide a convenience class for managing job-script files."""

import re

from loguru import logger


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: list[str]) -> str:
    """
    Inject sbatch params into job script.

    Given the job script as job_script_data_as_string, inject the sbatch params in the correct location.
    """
    logger.debug("Preparing to inject sbatch params into job script")

    if not sbatch_params:
        logger.warning("Sbatch param list is empty")
        return job_script_data_as_string

    # Find the first non-blank, non-comment line
    match = re.search(r"^[^#\n]", job_script_data_as_string, re.MULTILINE)
    if match:
        insert_index = match.start()
    else:
        # If no such line is found, append at the end
        insert_index = len(job_script_data_as_string)

    inner_string = "# Sbatch params injected at rendering time\n"
    for parameter in sbatch_params:
        inner_string += f"#SBATCH {parameter}\n"
    else:
        inner_string += "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:insert_index] + inner_string + job_script_data_as_string[insert_index:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string
