"""
Test the module config.
"""

from itertools import combinations

import pytest

from jobbergate_api.config import Settings, check_none_or_all_keys_exist


class TestCheckNoneOrAllKeysExist:
    """
    A class containing all tests for check_none_or_all_keys_exist.
    """

    keys = {"foo", "bar", "baz", "qux"}
    missing_keys = {k + "_missing" for k in keys}

    @pytest.fixture(scope="class")
    def dummy_dict(self) -> dict:
        """
        Build a dummy dict to be used as reference in the tests.
        """
        return {k: None for k in self.keys}

    @pytest.mark.parametrize("target_keys", combinations(keys, 3))
    def test_all_keys_exist(self, dummy_dict, target_keys):
        """
        Test if it returns true when all of the target keys exist in the input dict.
        """
        assert check_none_or_all_keys_exist(dummy_dict, set(target_keys)) is True

    @pytest.mark.parametrize("target_keys", combinations(missing_keys, 3))
    def test_none_keys_exist(self, dummy_dict, target_keys):
        """
        Test if it returns true when none of the target keys exists in the input dict.
        """
        assert check_none_or_all_keys_exist(dummy_dict, set(target_keys)) is True

    @pytest.mark.parametrize("target_keys", zip(keys, missing_keys))
    def test_some_keys_exist(self, dummy_dict, target_keys):
        """
        Test if it returns false when some of the target keys are missing in the input dict.
        """
        assert check_none_or_all_keys_exist(dummy_dict, set(target_keys)) is False


class TestSendgridSettings:
    """
    A class containing all tests for the sendgrid settings.

    The goal is to test if all params are defined and the notifications can be sent
    to the users, or if none of the params are defined and notifications can not
    be sent. If just some of them are defined, RuntimeError is raised.
    """

    SENDGRID_PARAMS = {"SENDGRID_FROM_EMAIL", "SENDGRID_API_KEY"}

    def test_all_keys_exist(self):
        """
        Test scenario where all of the sendgrid params are defined.
        """
        params = {k: "foo" for k in self.SENDGRID_PARAMS}
        settings = Settings(**params)
        assert all(getattr(settings, k) == "foo" for k in self.SENDGRID_PARAMS)

    def test_none_key_exist(self):
        """
        Test scenario where none of the sendgrid params are defined.

        Note: Empty strings can be used here because Settings filters them out.
        """
        params = {k: "" for k in self.SENDGRID_PARAMS}
        settings = Settings(**params)
        assert all(getattr(settings, k) is None for k in self.SENDGRID_PARAMS)

    @pytest.mark.parametrize("missing_param", SENDGRID_PARAMS)
    def test_some_key_exist(self, missing_param):
        """
        Test scenario where some of the parameters are defined, resulting in RuntimeError.

        Note: Empty strings can be used here because Settings filters them out.
        """
        params = {k: "" if k == missing_param else "foo" for k in self.SENDGRID_PARAMS}
        with pytest.raises(
            RuntimeError,
            match="Either none or all SendGrind parameters are expected",
        ):
            Settings(**params)
