import pytest

from jobbergate_agent.user_mapper.single_user import SingleUserMapper


class TestSingleUserMapper:
    """Test the SingleUserMapper class."""

    def test_init__success(self):
        """Test that the class is initialized successfully."""
        mapper = SingleUserMapper("test-user")

        assert mapper.slurm_user == "test-user"
        assert len(mapper) == 1
        assert list(mapper) == ["test-user"]
        assert "test-user" in mapper
        assert "another-test-user" in mapper

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

        assert mapper[user_email] == "test-user"
