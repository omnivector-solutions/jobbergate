"""Shared fixtures for the cluster API test suite."""

import pytest

from jobbergate_cluster_api.config import settings


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Point SESSIONS_DIR at a temp directory for the duration of a test."""
    target = tmp_path / "sessions"
    target.mkdir()
    monkeypatch.setattr(settings, "SESSIONS_DIR", target)
    return target
