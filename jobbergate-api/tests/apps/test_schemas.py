import pytest
from pydantic import ValidationError

from jobbergate_api.apps.schemas import BaseModel, LengthLimitedStr


class TestLengthLimitedStr:
    """
    Test the LengthLimitedStr type alias.
    """

    class DummySchema(BaseModel):
        """
        A dummy schema to test the LengthLimitedStr type alias.
        """

        name: LengthLimitedStr

    def test_valid(self):
        """
        Test that short strings are accepted.
        """
        expected_name = "a" * 255
        schema = self.DummySchema(name=expected_name)
        assert isinstance(schema.name, str)
        assert schema.name == expected_name

    def test_invalid(self):
        """
        Test that long strings are rejected.
        """
        with pytest.raises(ValidationError):
            self.DummySchema(name="a" * 256)
