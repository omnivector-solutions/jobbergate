"""
Provide to the agent a way to map email addresses from Jobbergate local Slurm users.

Custom mappers can be added to the agent as installable plugins, which are discovered at runtime.
"""

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from typing import Mapping, Protocol

from buzz import enforce_defined, require_condition

from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import logger
from jobbergate_agent.utils.plugin import load_plugins


SlurmUserMapper = Mapping[str, str]
"""
Slurm user mappers are mappings from email addresses to local Slurm users.
"""


class SlurmUserMapperFactory(Protocol):
    """
    Protocol to be implemented by plugins on client code.

    A callable with no arguments is expected in order to handle to client code
    the configuration and initialization of any custom user mapper.
    Any object that implements the ``Mapping`` protocol can be returned.
    """

    def __call__(self) -> SlurmUserMapper:
        """Specify the signature to build a user mapper."""
        ...


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


def manufacture() -> SlurmUserMapper:
    """Create an instance of a Slurm user mapper given the app configuration."""
    mappers = load_plugins("user_mapper")
    factory_function: SlurmUserMapperFactory = enforce_defined(
        mappers.get(SETTINGS.SLURM_USER_MAPPER or "single-user-mapper"),
        "No user mapper found for the name '{}', available mappers are: {}".format(
            SETTINGS.SLURM_USER_MAPPER, ", ".join(mappers.keys())
        ),
        raise_exc_class=KeyError,
    )
    logger.debug("Selected user-mapper: {}", SETTINGS.SLURM_USER_MAPPER)
    return factory_function()
