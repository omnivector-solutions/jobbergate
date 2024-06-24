from datetime import datetime

import pendulum
import pytest
from pydantic import ValidationError

from jobbergate_api.apps.schemas import BaseModel, LengthLimitedStr, PydanticDateTime


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


class TestPydanticDateTime:
    class DateTimeSchema(BaseModel):
        timestamp: PydanticDateTime

    def test_valid__with_pendulum_DateTime(self):
        expected_timestamp = pendulum.parse("2024-05-31 10:21:00")
        instance = self.DateTimeSchema(timestamp=pendulum.parse("2024-05-31 10:21:00"))
        assert isinstance(instance.timestamp, pendulum.DateTime)
        assert instance.timestamp == expected_timestamp

    def test_valid__with_standard_datetime(self):
        expected_timestamp = pendulum.parse("2024-05-31 10:21:00")
        instance = self.DateTimeSchema(timestamp=datetime(2024, 5, 31, 10, 21, 0))
        assert isinstance(instance.timestamp, pendulum.DateTime)
        assert instance.timestamp == expected_timestamp

    def test_valid__with_string_timestamp(self):
        expected_timestamp = pendulum.parse("2024-05-31 10:21:00")
        instance = self.DateTimeSchema(timestamp="2024-05-31 10:21:00")
        assert isinstance(instance.timestamp, pendulum.DateTime)
        assert instance.timestamp == expected_timestamp
