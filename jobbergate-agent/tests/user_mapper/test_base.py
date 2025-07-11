import pytest

from jobbergate_agent.user_mapper.base import manufacture
from jobbergate_agent.user_mapper.single_user import SingleUserMapper


class TestManufacture:
    """Test the manufacture function."""

    def test_manufacture__default_mapper(self):
        """Test that the default mapper is returned when no settings are set."""
        mapper = manufacture()

        assert isinstance(mapper, SingleUserMapper)

    def test_manufacture__not_found_error(self, tweak_settings):
        """Test that a KeyError is raised when the mapper is not found."""
        with tweak_settings(SLURM_USER_MAPPER="not-found"):
            with pytest.raises(KeyError):
                manufacture()
