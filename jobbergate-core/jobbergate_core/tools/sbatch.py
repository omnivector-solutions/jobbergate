from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Sequence

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

    # Default to inserting at the end of the file
    insert_index = len(job_script_data_as_string)
    # Find the first non-blank, non-comment line
    if match := re.search(r"^[^#\n]", job_script_data_as_string, re.MULTILINE):
        insert_index = match.start()

    inner_string = f"# {header}\n" if header else ""
    for parameter in sbatch_params:
        inner_string += f"#SBATCH {parameter}\n"
    inner_string += "\n"

    new_job_script_data_as_string = (
        job_script_data_as_string[:insert_index] + inner_string + job_script_data_as_string[insert_index:]
    )

    logger.debug("Done injecting sbatch params into job script")
    return new_job_script_data_as_string


@dataclass
class SubprocessHandler:
    def run(self, cmd: Sequence[str], **kwargs) -> subprocess.CompletedProcess:
        logger.debug("Running command '{}' with kwargs: {}", " ".join(cmd), kwargs)
        try:
            result = subprocess.run(cmd, check=True, shell=False, **kwargs)
            logger.trace("Command returned code {} with result: {}", result.returncode, result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            message = f"Failed to run command with code {e.returncode}: {e.stderr or e.stdout}"
            logger.error(message)
            raise RuntimeError(message) from e


@dataclass(frozen=True)
class InfoHandler:
    """Get info from jobs on the cluster."""

    scontrol_path: Path = Path("/usr/bin/scontrol")
    subprocess_handler: SubprocessHandler = field(default_factory=SubprocessHandler)

    def __post_init__(self):
        with check_expressions("Check paths", raise_exc_class=ValueError) as check:
            check(self.scontrol_path.is_absolute(), "scontrol_path is not an absolute path")
            check(self.scontrol_path.exists(), "scontrol_path does not exist")

    def get_job_info(self, slurm_id: int) -> dict[str, Any]:
        """Gets job info as the user."""
        command = (
            self.scontrol_path.as_posix(),
            "show",
            "job",
            shlex.quote(str(slurm_id)),
            "--json",
        )
        completed_process = self.subprocess_handler.run(command, capture_output=True, text=True)
        data = json.loads(completed_process.stdout)
        try:
            job_info = data["jobs"][0]
            logger.debug(f"Information for {slurm_id=} is: {job_info}")
            return job_info
        except KeyError as e:
            message = f"Failed to parse job info from {completed_process.stdout}"
            logger.error(message)
            raise RuntimeError(message) from e
        except IndexError as e:
            message = f"Job not fount: {slurm_id}"
            logger.warning(message)
            raise RuntimeError(message) from e


@dataclass(frozen=True)
class SubmissionHandler:
    """Submits sbatch jobs to the cluster."""

    sbatch_path: Path = Path("/usr/bin/sbatch")
    submission_directory: Path = field(default_factory=Path.cwd)
    subprocess_handler: SubprocessHandler = field(default_factory=SubprocessHandler)

    sbatch_output_parser: ClassVar[re.Pattern] = re.compile(r"^(?P<id>\d+)(,(?P<cluster_name>.+))?$")

    def __post_init__(self):
        with check_expressions("Check paths", raise_exc_class=ValueError) as check:
            check(self.sbatch_path.is_absolute(), "sbatch_path is not an absolute path")
            check(self.sbatch_path.exists(), "sbatch_path does not exist")
            check(self.submission_directory.is_absolute(), "submission_directory is not an absolute path")

    def submit_job(self, job_script_path: Path) -> int:
        """Runs sbatch as the user to submit a job script and returns the slurm id assigned to it."""
        command = (
            self.sbatch_path.as_posix(),
            "--parsable",
            job_script_path.as_posix(),
        )

        completed_process = self.subprocess_handler.run(
            command, cwd=self.submission_directory, capture_output=True, text=True
        )

        if match := self.sbatch_output_parser.match(completed_process.stdout):
            slurm_id = int(match.group("id"))
            logger.debug(f"Submission succeeded with {slurm_id=}")
            return slurm_id
        message = f"Failed to parse slurm job id from {completed_process.stdout}"
        logger.error(message)
        raise RuntimeError(message)

    def copy_file_to_submission_directory(self, source_file: Path) -> Path:
        """Copies the job file to the submission directory as the user."""
        # Reference: https://stackoverflow.com/a/71589233
        destination_file = self.submission_directory / source_file.name
        command = ("tee", destination_file.as_posix())
        try:
            with source_file.open("rb") as source:
                self.subprocess_handler.run(
                    command,
                    stdin=source,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except IOError as e:
            message = f"Failed to copy file to submission directory: {e}"
            logger.error(message)
            raise RuntimeError(message) from e
        return destination_file


@dataclass(frozen=True)
class ScancelHandler:
    """Cancels jobs on the cluster."""

    scancel_path: Path = Path("/usr/bin/scancel")
    subprocess_handler: SubprocessHandler = field(default_factory=SubprocessHandler)

    def __post_init__(self):
        with check_expressions("Check paths", raise_exc_class=ValueError) as check:
            check(self.scancel_path.is_absolute(), "scancel_path is not an absolute path")
            check(self.scancel_path.exists(), "scancel_path does not exist")

    def cancel_job(self, slurm_id: int) -> None:
        """Cancels a job with the given slurm id."""
        command = (self.scancel_path.as_posix(), str(slurm_id))
        self.subprocess_handler.run(command, capture_output=True, text=True)
        logger.debug(f"Cancelled job with {slurm_id=}")
