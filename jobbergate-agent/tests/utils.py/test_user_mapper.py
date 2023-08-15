import pytest

from jobbergate_agent.utils.user_mapper import SingleUserMapper, manufacture


class TestSingleUserMapper:
    """Test the SingleUserMapper class."""

    def test_init__success(self):
        """Test that the class is initialized successfully."""
        mapper = SingleUserMapper("test-user")

        assert mapper.slurm_user == "test-user"

    def test_init__default_to_settings(self, tweak_settings):
        """Test that the class is initialized successfully with default value."""
        with tweak_settings(SINGLE_USER_SUBMITTER="another-test-user"):
            mapper = SingleUserMapper()

        assert mapper.slurm_user == "another-test-user"

    def test_init__settings_are_low_priority(self, tweak_settings):
        """Test that the class is initialized and the argument takes priority over settings."""
        with tweak_settings(SINGLE_USER_SUBMITTER="another-test-user"):
            mapper = SingleUserMapper("test-user")

        assert mapper.slurm_user == "test-user"

    def test_init__fail(self, tweak_settings):
        """Test that the class is not initialized when user_submitter is empty."""
        with tweak_settings(SINGLE_USER_SUBMITTER=None):
            with pytest.raises(ValueError):
                SingleUserMapper()

    @pytest.mark.parametrize("user_email", ["test-email", "another-test-email"])
    def test_getitem(self, user_email):
        """Test that the class returns the correct user."""
        mapper = SingleUserMapper("test-user")

        assert mapper(user_email) == "test-user"


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
