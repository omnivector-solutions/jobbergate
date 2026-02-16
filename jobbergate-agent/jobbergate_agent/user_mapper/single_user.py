"""This module defines a user mapper that always returns the same user."""

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass

from buzz import require_condition

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import logger


@dataclass
class SingleUserMapper(MappingABC):
    """A user mapper that always returns the same user."""

    slurm_user: str = ""

    def __post_init__(self):
        """Validate the user mapper by asserting it is not an empty string."""
        if not self.slurm_user and SETTINGS.SINGLE_USER_SUBMITTER:
            self.slurm_user = SETTINGS.SINGLE_USER_SUBMITTER
        require_condition(
            len(self.slurm_user) > 0,
            "No username was set for single-user job submission.",
            raise_exc_class=ValueError,
        )
        logger.info(f"Started the single-user-mapper with {self.slurm_user=}")

    def __getitem__(self, _: str) -> str:
        return self.slurm_user

    def __iter__(self):
        yield self.slurm_user

    def __len__(self):
        return 1
