"""
FastAPI application for the Jobbergate Cluster API.

Routes:
- ``POST   /jobbergate/sessions``                    create an interactive session
- ``GET    /jobbergate/sessions/{id}``               poll session status
- ``DELETE /jobbergate/sessions/{id}``               cancel a session
- ``GET    /jobbergate/sessions/{id}/terminal/...``  proxied ttyd page/assets (OTP guarded)
- ``WS     /jobbergate/sessions/{id}/terminal/ws``   proxied ttyd websocket (OTP guarded)
- ``GET    /jobbergate/health``                      liveness
"""

import secrets
from typing import Annotated

from armasec import TokenPayload
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, status
from loguru import logger

from jobbergate_cluster_api import __version__, sessions
from jobbergate_cluster_api.config import settings
from jobbergate_cluster_api.proxy import proxy_http, proxy_websocket
from jobbergate_cluster_api.schemas import SessionCreateRequest, SessionCreateResponse, SessionDetail, SessionStatus
from jobbergate_cluster_api.security import get_bearer_token, lockdown_session
from jobbergate_cluster_api.slurm import SlurmError

app = FastAPI(title="Jobbergate Cluster API", version=__version__)

_OTP_COOKIE = "jg_session_otp_{session_id}"


def _load_session_or_404(session_id: str) -> sessions.Session:
    try:
        return sessions.load_session(session_id)
    except sessions.SessionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} was not found")


def _terminal_url(session_id: str) -> str:
    return f"{settings.BASE_PATH}/{session_id}/terminal/"


def _detail(session: sessions.Session) -> SessionDetail:
    session_status, exit_code = sessions.session_status(session)
    if session_status in (SessionStatus.FINISHED, SessionStatus.FAILED, SessionStatus.CANCELLED):
        sessions.shred_credentials(session)
    return SessionDetail(
        session_id=session.session_id,
        status=session_status,
        application_selector=session.application_selector,
        slurm_job_id=session.slurm_job_id,
        created_at=session.created_at,
        url=_terminal_url(session.session_id) if session_status is SessionStatus.RUNNING else None,
        exit_code=exit_code,
        owner_email=session.owner_email,
    )


def _check_otp(session: sessions.Session, request: Request | WebSocket) -> bool:
    """The OTP may arrive as a query param (first page load) or as the session cookie."""
    candidate = request.query_params.get("otp") or request.cookies.get(
        _OTP_COOKIE.format(session_id=session.session_id), ""
    )
    return secrets.compare_digest(candidate, session.otp)


@app.get("/jobbergate/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.post(
    "/jobbergate/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: SessionCreateRequest,
    access_token: Annotated[str, Depends(get_bearer_token)],
    token_payload: Annotated[TokenPayload, Depends(lockdown_session)],
):
    """
    Open an interactive session for the given application: seed the caller's tokens,
    sbatch the ttyd session job into the sessions partition, and return the terminal
    URL plus its one-time password (returned only once, here).
    """
    try:
        session = sessions.create_session(
            selector=payload.selector,
            access_token=access_token,
            refresh_token=payload.refresh_token,
            owner_email=getattr(token_payload, "email", None),
        )
    except SlurmError as err:
        logger.error("Failed to submit session job: {}", err)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(err))
    detail = _detail(session)
    return SessionCreateResponse(**detail.model_dump(exclude={"url"}), url=_terminal_url(session.session_id), otp=session.otp)


@app.get("/jobbergate/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    token_payload: Annotated[TokenPayload, Depends(lockdown_session)],
):
    return _detail(_load_session_or_404(session_id))


@app.delete("/jobbergate/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(
    session_id: str,
    token_payload: Annotated[TokenPayload, Depends(lockdown_session)],
):
    sessions.cancel_session(_load_session_or_404(session_id))


@app.websocket("/jobbergate/sessions/{session_id}/terminal/ws")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    session = _load_session_or_404(session_id)
    if not _check_otp(session, websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    endpoint = sessions.session_endpoint(session)
    if endpoint is None:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return
    await proxy_websocket(endpoint, f"{settings.BASE_PATH}/{session_id}/terminal/ws", websocket)


@app.api_route(
    "/jobbergate/sessions/{session_id}/terminal/{asset_path:path}",
    methods=["GET", "POST"],
    include_in_schema=False,
)
async def terminal_assets(session_id: str, asset_path: str, request: Request) -> Response:
    """
    Proxy the ttyd page and its assets. A valid ``?otp=`` on the first load is
    exchanged for a session-scoped cookie so relative asset requests pass the guard.
    """
    session = _load_session_or_404(session_id)
    if not _check_otp(session, request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing session OTP")
    endpoint = sessions.session_endpoint(session)
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The session terminal is not up yet - poll the session status until RUNNING",
        )
    response = await proxy_http(endpoint, f"{settings.BASE_PATH}/{session_id}/terminal/{asset_path}", request)
    if request.query_params.get("otp"):
        response.set_cookie(
            _OTP_COOKIE.format(session_id=session_id),
            session.otp,
            httponly=True,
            samesite="strict",
            path=f"{settings.BASE_PATH}/{session_id}/",
        )
    return response
