"""Tests for the API routes with the auth guard overridden."""

import pytest
from fastapi.testclient import TestClient

from jobbergate_cluster_api import sessions
from jobbergate_cluster_api.main import app
from jobbergate_cluster_api.security import lockdown_session


class FakeTokenPayload:
    email = "user@test.com"


@pytest.fixture
def client(sessions_dir):
    app.dependency_overrides[lockdown_session] = lambda: FakeTokenPayload()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_sbatch(mocker):
    return mocker.patch("jobbergate_cluster_api.sessions.slurm.sbatch", return_value=77)


class TestHealth:
    def test_health(self, client):
        response = client.get("/jobbergate/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestCreateSession:
    def test_create_returns_otp_and_url(self, client, mock_sbatch, mocker):
        mocker.patch("jobbergate_cluster_api.sessions.slurm.job_state", return_value="PENDING")
        response = client.post(
            "/jobbergate/sessions",
            json={"application_identifier": "simple-application"},
            headers={"Authorization": "Bearer access-abc"},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["slurm_job_id"] == 77
        assert data["otp"]
        assert data["url"].endswith(f"/sessions/{data['session_id']}/terminal/")
        assert data["owner_email"] == "user@test.com"

    def test_create_without_bearer_is_401(self, client, mock_sbatch):
        response = client.post("/jobbergate/sessions", json={"application_id": 1})
        assert response.status_code == 401

    def test_create_with_both_selectors_is_422(self, client, mock_sbatch):
        response = client.post(
            "/jobbergate/sessions",
            json={"application_id": 1, "application_identifier": "x"},
            headers={"Authorization": "Bearer access-abc"},
        )
        assert response.status_code == 422


class TestGetSession:
    def test_get_missing_is_404(self, client):
        response = client.get("/jobbergate/sessions/nope")
        assert response.status_code == 404

    def test_get_running_session_exposes_url(self, client, mock_sbatch, mocker):
        session = sessions.create_session("42", "access-abc")
        mocker.patch("jobbergate_cluster_api.sessions.slurm.job_state", return_value="RUNNING")
        (session.session_dir / "endpoint").write_text("c1:40123")

        response = client.get(f"/jobbergate/sessions/{session.session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RUNNING"
        assert data["url"] is not None

    def test_finished_session_shreds_tokens(self, client, mock_sbatch):
        session = sessions.create_session("42", "access-abc")
        (session.session_dir / "exit_code").write_text("0")

        response = client.get(f"/jobbergate/sessions/{session.session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "FINISHED"
        assert not (session.session_dir / "cache" / "token").exists()


class TestCancelSession:
    def test_cancel_scancels_and_shreds(self, client, mock_sbatch, mocker):
        mock_scancel = mocker.patch("jobbergate_cluster_api.sessions.slurm.scancel")
        session = sessions.create_session("42", "access-abc")

        response = client.delete(f"/jobbergate/sessions/{session.session_id}")
        assert response.status_code == 204
        mock_scancel.assert_called_once_with(77)
        assert not (session.session_dir / "cache" / "token").exists()


class TestTerminalGuard:
    def test_terminal_without_otp_is_403(self, client, mock_sbatch):
        session = sessions.create_session("42", "access-abc")
        response = client.get(f"/jobbergate/sessions/{session.session_id}/terminal/")
        assert response.status_code == 403

    def test_terminal_with_otp_before_endpoint_is_409(self, client, mock_sbatch):
        session = sessions.create_session("42", "access-abc")
        response = client.get(f"/jobbergate/sessions/{session.session_id}/terminal/?otp={session.otp}")
        assert response.status_code == 409
