"""
Provide to the agent a way to map email addresses from Jobbergate local Slurm users.

Custom mappers can be added to the agent as installable plugins, which are discovered at runtime.
"""

from typing import Mapping, Protocol

from buzz import enforce_defined

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
