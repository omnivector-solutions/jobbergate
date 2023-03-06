"""
Test s3 manager.
"""

import pytest
from boto3 import client

from jobbergate_api.s3_manager import engine_factory


class TestEngineFactory:
    """
    Test the engine factory.
    """

    @pytest.fixture(scope="class")
    def client(self):
        """
        Fixture with a dummy client for testing.
        """
        return client("s3")

    @pytest.fixture(scope="class")
    def s3_engine(self, client):
        """
        Fixture with a dummy s3 engine factory for testing.
        """
        return engine_factory(
            s3_client=client,
            bucket_name="test-bucket",
            prefix="test-dir",
        )

    def test_client(self, s3_engine, client):
        """
        Assert the client has the expected value.
        """
        assert s3_engine.s3_client == client

    def test_bucket_name(self, s3_engine):
        """
        Assert the bucket_name has the expected value.
        """
        assert s3_engine.bucket_name == "test-bucket"

    def test_prefix(self, s3_engine):
        """
        Assert the prefix has the expected value.
        """
        assert s3_engine.prefix == "test-dir"
