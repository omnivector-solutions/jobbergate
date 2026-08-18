"""Tests for session creation, script rendering, and status mapping."""

import json

import pytest

from jobbergate_cluster_api import sessions
from jobbergate_cluster_api.config import settings
from jobbergate_cluster_api.schemas import SessionCreateRequest, SessionStatus


class TestRenderSessionScript:
    def test_renders_expected_command_and_env(self, sessions_dir):
        session_dir = sessions_dir / "abc123"
        script = sessions.render_session_script("abc123", session_dir, "simple-application")

        assert f"#SBATCH --partition={settings.SESSIONS_PARTITION}" in script
        assert f"export JOBBERGATE_CACHE_DIR={session_dir}/cache" in script
        assert f"export SBATCH_PATH={settings.SBATCH_PATH}" in script
        assert "ttyd --once --writable" in script
        assert f"--base-path {settings.BASE_PATH}/abc123/terminal" in script
        assert "jobbergate job-scripts create simple-application" in script
        assert f"--submit --cluster-name {settings.CLUSTER_NAME}" in script
        # bash runtime variables survived templating
        assert '${PORT}' in script
        assert "$(hostname)" in script

    def test_numeric_selector(self, sessions_dir):
        script = sessions.render_session_script("abc123", sessions_dir / "abc123", "42")
        assert "jobbergate job-scripts create 42" in script


class TestCreateSession:
    @pytest.fixture
    def mock_sbatch(self, mocker):
        return mocker.patch("jobbergate_cluster_api.sessions.slurm.sbatch", return_value=123)

    def test_seeds_token_cache_and_submits(self, sessions_dir, mock_sbatch):
        session = sessions.create_session("simple-application", "access-abc", "refresh-xyz", "user@test.com")

        session_dir = sessions_dir / session.session_id
        assert (session_dir / "cache" / "token" / "access.token").read_text() == "access-abc"
        assert (session_dir / "cache" / "token" / "refresh.token").read_text() == "refresh-xyz"
        assert (session_dir / "cache" / "token" / "access.token").stat().st_mode & 0o777 == 0o600
        assert (session_dir / "work").is_dir()
        assert session.slurm_job_id == 123
        mock_sbatch.assert_called_once_with(session_dir / "session-job.sh")

    def test_meta_json_round_trip(self, sessions_dir, mock_sbatch):
        created = sessions.create_session("42", "access-abc")
        loaded = sessions.load_session(created.session_id)
        assert loaded == created

    def test_load_missing_session_raises(self, sessions_dir):
        with pytest.raises(sessions.SessionNotFound):
            sessions.load_session("nope")

    def test_no_refresh_token(self, sessions_dir, mock_sbatch):
        session = sessions.create_session("42", "access-abc")
        token_dir = sessions_dir / session.session_id / "cache" / "token"
        assert not (token_dir / "refresh.token").exists()


class TestSessionStatus:
    @pytest.fixture
    def session(self, sessions_dir, mocker):
        mocker.patch("jobbergate_cluster_api.sessions.slurm.sbatch", return_value=123)
        return sessions.create_session("42", "access-abc")

    def test_exit_code_zero_is_finished(self, session):
        (session.session_dir / "exit_code").write_text("0")
        assert sessions.session_status(session) == (SessionStatus.FINISHED, 0)

    def test_exit_code_nonzero_is_failed(self, session):
        (session.session_dir / "exit_code").write_text("1")
        assert sessions.session_status(session) == (SessionStatus.FAILED, 1)

    @pytest.mark.parametrize(
        "slurm_state,expected",
        [
            ("PENDING", SessionStatus.PENDING),
            ("COMPLETED", SessionStatus.FINISHED),
            ("FAILED", SessionStatus.FAILED),
            ("CANCELLED", SessionStatus.CANCELLED),
            ("TIMEOUT", SessionStatus.FAILED),
            (None, SessionStatus.UNKNOWN),
        ],
    )
    def test_slurm_state_mapping(self, session, mocker, slurm_state, expected):
        mocker.patch("jobbergate_cluster_api.sessions.slurm.job_state", return_value=slurm_state)
        assert sessions.session_status(session) == (expected, None)

    def test_running_without_endpoint_is_pending(self, session, mocker):
        mocker.patch("jobbergate_cluster_api.sessions.slurm.job_state", return_value="RUNNING")
        assert sessions.session_status(session)[0] is SessionStatus.PENDING

    def test_running_with_endpoint_is_running(self, session, mocker):
        mocker.patch("jobbergate_cluster_api.sessions.slurm.job_state", return_value="RUNNING")
        (session.session_dir / "endpoint").write_text("c1:40123")
        assert sessions.session_status(session)[0] is SessionStatus.RUNNING
        assert sessions.session_endpoint(session) == "c1:40123"

    def test_shred_credentials(self, session):
        sessions.shred_credentials(session)
        assert not (session.session_dir / "cache" / "token").exists()
        # meta and workdir survive for auditing
        assert (session.session_dir / "meta.json").exists()


class TestSessionCreateRequest:
    def test_requires_exactly_one_selector(self):
        with pytest.raises(ValueError):
            SessionCreateRequest()
        with pytest.raises(ValueError):
            SessionCreateRequest(application_id=1, application_identifier="x")

    def test_selector_prefers_supplied_field(self):
        assert SessionCreateRequest(application_id=42).selector == "42"
        assert SessionCreateRequest(application_identifier="simple").selector == "simple"
