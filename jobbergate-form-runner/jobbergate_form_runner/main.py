"""
The Form Runner service: REST + SSE endpoints driving cluster-side application question flows.

Public endpoints (armasec-locked, session-owner-bound) serve the embeddable web form; internal
endpoints (session-secret-locked) serve the runner job executing ``jobbergate job-scripts
create-web-runner`` on the cluster. See jobbergate-form-runner/README.md for the protocol.
"""

import asyncio
import json
import secrets
from importlib import resources
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from loguru import logger
from pydantic import BaseModel

from jobbergate_form_runner import launcher, security
from jobbergate_form_runner.config import settings
from jobbergate_form_runner.security import Identity, locked_identity
from jobbergate_form_runner.sessions import TERMINAL_STATUSES, Session, store

app = FastAPI(title="Jobbergate Form Runner")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ----------------------------------------------------------------------- request models


class CreateSessionRequest(BaseModel):
    application_id_or_identifier: str | int
    # Optional refresh token so interviews longer than the access-token TTL keep working:
    # the runner's auth handler refreshes silently instead of demanding a new login
    refresh_token: str | None = None
    name: str | None = None
    fast: bool = False
    submit: bool = False
    cluster_name: str | None = None
    execution_directory: str | None = None
    sbatch_params: list[str] | None = None
    supplied_params: dict[str, Any] | None = None


class AnswerRequest(BaseModel):
    variablename: str
    value: Any


class QuestionRequest(BaseModel):
    question: dict[str, Any]
    auto: bool = False
    value: Any = None


class VerdictRequest(BaseModel):
    accepted: bool
    message: str | None = None
    value: Any = None


class FinishRequest(BaseModel):
    status: str
    result: dict[str, Any] | None = None
    message: str | None = None


# ----------------------------------------------------------------------------- helpers


async def session_access(
    session_id: str,
    request: Request,
    x_session_key: Annotated[str | None, Header()] = None,
) -> Session:
    """Resolve a session for its owner: either by the short per-session web key (what the
    form URL carries in its fragment) or by a full OIDC token with the owner's ``sub``."""
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "Unknown session")
    if x_session_key is not None:
        if not secrets.compare_digest(x_session_key, session.web_key):
            raise HTTPException(403, "Invalid session key")
        return session
    identity = await security.identify_request(request)
    if session.owner_sub != identity.sub:
        raise HTTPException(403, "You are not the owner of this session")
    return session


def bridge_session(session_id: str, secret: str | None) -> Session:
    session = store.get(session_id)
    if session is None or not secret or secret != session.secret:
        raise HTTPException(403, "Invalid session credentials")
    return session


# --------------------------------------------------------------------- public endpoints


@app.get("/form-runner/health")
async def health():
    return {"status": "ok"}


@app.get("/form-runner/form")
async def form_page():
    """The embeddable web form (authenticates itself with the token in the URL fragment)."""
    static = resources.files("jobbergate_form_runner") / "static" / "form.html"
    return FileResponse(str(static), media_type="text/html")


@app.post("/form-runner/sessions", status_code=201)
async def create_session(body: CreateSessionRequest, identity: Annotated[Identity, Depends(locked_identity)],
                         authorization: Annotated[str | None, Header()] = None):
    # A session renders a job script, and optionally submits it right away — require the
    # matching write scopes up front so the runner does not fail halfway through
    required = [security.JOB_SCRIPTS_CREATE]
    if body.submit:
        required.append(security.JOB_SUBMISSIONS_CREATE)
    identity.require_permissions(*required)

    access_token = (authorization or "").split(" ", 1)[-1]
    session = Session(
        owner_sub=identity.sub,
        owner_email=identity.email,
        access_token=access_token,
        application_id_or_identifier=str(body.application_id_or_identifier),
        options=body.model_dump(exclude={"application_id_or_identifier"}),
    )
    session.loop = asyncio.get_running_loop()
    store.add(session)

    def mark_failed(message: str) -> None:
        # invoked from the launcher's watcher thread when the runner dies without reporting
        session.finish("failed", {"message": message})

    try:
        await asyncio.to_thread(launcher.launch, session, mark_failed)
    except Exception as err:
        logger.exception("Failed to launch runner for session {}", session.id)
        session.finish("failed", {"message": f"Could not launch the runner job: {err}"})
        raise HTTPException(502, f"Could not launch the runner job: {err}") from err
    return {
        "session_id": session.id,
        "status": session.status,
        "web_key": session.web_key,
        # The key travels in the URL fragment: short, and never sent to any server
        "form_url": f"{settings.PUBLIC_URL.rstrip('/')}/form-runner/form?session_id={session.id}#key={session.web_key}",
    }


@app.get("/form-runner/sessions/{session_id}")
async def snapshot(session: Annotated[Session, Depends(session_access)]):
    return {
        "session_id": session.id,
        "status": session.status,
        "slurm_job_id": session.slurm_job_id,
        "pending_question": session.pending_question,
        "last_event_id": len(session.events),
    }


@app.post("/form-runner/sessions/{session_id}/answers")
async def post_answer(body: AnswerRequest, session: Annotated[Session, Depends(session_access)]):
    pending = session.pending_question
    if pending is None or pending.get("variablename") != body.variablename:
        raise HTTPException(409, "No such question is pending")
    if len(json.dumps(body.value)) > settings.MAX_ANSWER_CHARS:
        return JSONResponse(
            status_code=422,
            content={"accepted": False, "message": f"Answer is too long (max {settings.MAX_ANSWER_CHARS} characters)."},
        )
    try:
        verdict = await session.submit_answer(body.value)
    except asyncio.TimeoutError as err:
        raise HTTPException(504, "The runner did not validate the answer in time") from err
    if not verdict["accepted"]:
        return JSONResponse(status_code=422, content=verdict)
    return verdict


@app.delete("/form-runner/sessions/{session_id}", status_code=204)
async def cancel_session(session: Annotated[Session, Depends(session_access)]):
    if session.status not in TERMINAL_STATUSES:
        await asyncio.to_thread(launcher.cancel, session)
        session.status = "cancelled"
        session.emit("failed", {"message": "Session cancelled."})


@app.get("/form-runner/sessions/{session_id}/events")
async def events(
    request: Request,
    session: Annotated[Session, Depends(session_access)],
    last_event_id: Annotated[str | None, Header()] = None,
):
    start_after = int(last_event_id or 0)

    async def stream():
        cursor = start_after
        while True:
            while cursor < len(session.events):
                event_id, event, data = session.events[cursor]
                cursor += 1
                yield f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data)}\n\n"
                if event in ("completed", "failed"):
                    return
            session.new_event.clear()
            try:
                await asyncio.wait_for(session.new_event.wait(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
            if await request.is_disconnected():
                return

    return StreamingResponse(stream(), media_type="text/event-stream")


# ----------------------------------------------------- internal bridge (runner-facing)


@app.get("/form-runner/internal/sessions/{session_id}/context")
async def bridge_context(session_id: str, x_session_secret: Annotated[str | None, Header()] = None):
    session = bridge_session(session_id, x_session_secret)
    if session.status == "queued":
        session.set_status("in_progress")
    return {
        "application_id_or_identifier": session.application_id_or_identifier,
        "access_token": session.access_token,
        **session.options,
    }


@app.post("/form-runner/internal/sessions/{session_id}/questions")
async def bridge_question(
    session_id: str, body: QuestionRequest, x_session_secret: Annotated[str | None, Header()] = None
):
    session = bridge_session(session_id, x_session_secret)
    if body.auto:
        session.publish_auto_answer(body.question, body.value)
    else:
        session.publish_question(body.question)
    return {}


@app.get("/form-runner/internal/sessions/{session_id}/answer")
async def bridge_answer(
    session_id: str, wait: float = 30, x_session_secret: Annotated[str | None, Header()] = None
):
    session = bridge_session(session_id, x_session_secret)
    available, value = await session.await_answer(min(wait, 55))
    if not available:
        return Response(status_code=204)
    return {"value": value}


@app.post("/form-runner/internal/sessions/{session_id}/verdict")
async def bridge_verdict(
    session_id: str, body: VerdictRequest, x_session_secret: Annotated[str | None, Header()] = None
):
    session = bridge_session(session_id, x_session_secret)
    session.publish_verdict(body.accepted, body.message, body.value)
    return {}


@app.post("/form-runner/internal/sessions/{session_id}/finish")
async def bridge_finish(
    session_id: str, body: FinishRequest, x_session_secret: Annotated[str | None, Header()] = None
):
    session = bridge_session(session_id, x_session_secret)
    if body.status == "completed":
        session.finish("completed", body.result or {})
    else:
        session.finish("failed", {"message": body.message or "The runner reported a failure."})
    return {}
