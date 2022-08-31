"""
Test s3 manager.
"""

from pathlib import Path

import pytest
from boto3 import client
from jobbergate_api.s3_manager import engine_factory


class TestEngineFactory:
    @pytest.fixture(scope="class")
    def client(self):
        return client("s3")

    @pytest.fixture(scope="class")
    def s3_engine(self, client):
        return engine_factory(
            s3_client=client,
            bucket_name="test-bucket",
            work_directory=Path("test-dir"),
        )

    def test_client(self, s3_engine, client):
        assert s3_engine.s3_client == client

    def test_bucket_name(self, s3_engine):
        assert s3_engine.bucket_name == "test-bucket"

    def test_prefix(self, s3_engine):
        assert s3_engine.prefix == "test-dir"
