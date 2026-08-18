"""
Schema definitions for the cluster API sessions.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator


class SessionStatus(str, Enum):
    """
    Lifecycle of an interactive session.

    PENDING: session job submitted, waiting for the node / ttyd to come up.
    RUNNING: ttyd is up and the terminal can be attached.
    FINISHED: the CLI exited cleanly (job script created and submitted).
    FAILED: the CLI or the session job exited with an error.
    CANCELLED: cancelled via the API or scancel.
    UNKNOWN: slurm no longer knows the job and no exit code was recorded.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class SessionCreateRequest(BaseModel):
    """
    Payload to open a new interactive session.

    Exactly one of ``application_id`` or ``application_identifier`` must be supplied.
    The refresh token is optional; when given, it is seeded alongside the access token
    so the CLI can renew credentials on long sessions.
    """

    application_id: int | None = None
    application_identifier: str | None = None
    sbatch_params: list[str] | None = None
    refresh_token: str | None = None

    @model_validator(mode="after")
    def _exactly_one_selector(self) -> "SessionCreateRequest":
        if (self.application_id is None) == (self.application_identifier is None):
            raise ValueError("Supply exactly one of application_id or application_identifier")
        return self

    @property
    def selector(self) -> str:
        return str(self.application_id) if self.application_id is not None else str(self.application_identifier)


class SessionDetail(BaseModel):
    """
    Session status as reported by ``GET /sessions/{id}``.
    """

    session_id: str
    status: SessionStatus
    application_selector: str
    slurm_job_id: int | None = None
    created_at: datetime | None = None
    url: str | None = None
    exit_code: int | None = None
    owner_email: str | None = None


class SessionCreateResponse(SessionDetail):
    """
    Response for session creation; the one-time password is only ever returned here.
    """

    otp: str
