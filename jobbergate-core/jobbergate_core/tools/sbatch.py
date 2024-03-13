from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Iterable

from buzz import check_expressions
from loguru import logger


def inject_sbatch_params(job_script_data_as_string: str, sbatch_params: list[str], header: str | None = None) -> str:
    """
    Injects sbatch parameters into a job script.

    This function takes a job script as a string, a list of sbatch parameters, and an optional header.

    Args:
        job_script_data_as_string: The job script as a string.
        sbatch_params: A list of sbatch parameters to be inserted.
        header: A comment to be inserted before the parameters (i.e., "Injected at runtime by Jobbergate").

    Returns:
        The job script with the sbatch parameters inserted.
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

    inner_string = f"# {header}\n" if header else ""
    for parameter in sbatch_params:
        inner_string += f"#SBATCH {parameter}\n"
    inner_string += "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:insert_index] + inner_string + job_script_data_as_string[insert_index:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


@dataclass(frozen=True)
class SbatchHandler:
    """Submits sbatch jobs to the cluster."""

    username: str
    sbatch_path: Path
    scontrol_path: Path
    submission_directory: Path = field(default_factory=Path)

    sbatch_output_parser: ClassVar[re.Pattern] = re.compile(r"^(?P<id>\d+)(,(?P<cluster_name>.+))?$")

    def __post_init__(self):
        with check_expressions("Check paths", raise_exc_class=ValueError) as check:
            check(self.sbatch_path.is_absolute(), "sbatch_path is not an absolute path")
            check(self.sbatch_path.exists(), "sbatch_path does not exist")
            check(self.scontrol_path.is_absolute(), "scontrol_path is not an absolute path")
            check(self.scontrol_path.exists(), "scontrol_path does not exist")

    def run(self, job_script_path: Path) -> int:
        """Runs sbatch as the user to submit a job script and returns the slurm id assigned to it."""
        command = (
            self.sbatch_path.as_posix(),
            "--parsable",
            job_script_path.as_posix(),
        )

        completed_process = self._run_command_as_user(
            command, cwd=self.submission_directory, capture_output=True, text=True
        )

        if match := self.sbatch_output_parser.match(completed_process.stdout):
            return int(match.group("id"))
        message = f"Failed to parse slurm job id from {completed_process.stdout}"
        logger.error(message)
        raise RuntimeError(message)

    def get_job_info(self, job_id: int) -> str:
        """Gets job info as the user."""
        command = (
            self.scontrol_path.as_posix(),
            "show",
            "job",
            str(job_id),
            "--json",
        )
        completed_process = self._run_command_as_user(command, capture_output=True, text=True)
        data = json.loads(completed_process.stdout)
        try:
            return json.dumps(data["jobs"][0])
        except KeyError as e:
            message = f"Failed to parse job info from {completed_process.stdout}"
            logger.error(message)
            raise RuntimeError(message) from e
        except IndexError as e:
            message = f"Job not fount: {job_id}"
            logger.warning(message)
            raise RuntimeError(message) from e

    def copy_file_to_submission_directory(self, source_file: Path) -> Path:
        """Copies the job file to the submission directory as the user."""
        # Reference: https://stackoverflow.com/a/71589233
        destination_file = self.submission_directory / source_file.name
        command = ("tee", destination_file.as_posix())
        try:
            with source_file.open("rb") as source:
                self._run_command_as_user(
                    command,
                    stdin=source,
                    stdout=subprocess.DEVNULL,
                )
        except IOError as e:
            message = f"Failed to copy file to submission directory: {e}"
            logger.error(message)
            raise RuntimeError(message) from e
        return destination_file

    def create_submission_directory(self) -> Path:
        """Creates a submission directory as the user."""
        command = ("mkdir", "--parents", self.submission_directory.as_posix())
        self._run_command_as_user(command)
        return self.submission_directory

    def _run_command_as_user(self, cmd: Iterable[str], **kwargs) -> subprocess.CompletedProcess:
        """Runs a command as the user."""
        quoted_cmd = [shlex.quote(arg) for arg in cmd]
        kwargs["user"] = self.username
        kwargs["check"] = True
        logger.debug("Running command '{}' with kwargs: {}", " ".join(quoted_cmd), kwargs)
        try:
            result = subprocess.run(quoted_cmd, **kwargs)
            logger.debug("Command returned code {} with result: {}", result.returncode, result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            message = f"Failed to run command with code {e.returncode}: {e.stderr}"
            logger.error(message)
            raise RuntimeError(message) from e
