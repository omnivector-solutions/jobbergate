"""
Session state for the Form Runner.

Each session couples one browser (the session owner, answering questions) with one runner job
(executing the SME application on the cluster). The service in between holds:

- a replayable **event log** feeding the browser's SSE stream (``Last-Event-ID`` resumes it);
- the **bridge synchronization**: the runner long-polls for answers, the browser's answer POST
  awaits the runner's validation verdict.
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any

TERMINAL_STATUSES = ("completed", "failed", "cancelled")


@dataclass
class Session:
    """One web question-flow session."""

    owner_sub: str
    owner_email: str | None
    access_token: str
    application_id_or_identifier: str
    options: dict[str, Any]

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    # Short capability key for the web form (travels in the URL fragment instead of the
    # much longer JWT — the runner already holds the real user token via the bridge)
    web_key: str = field(default_factory=lambda: secrets.token_urlsafe(12))
    status: str = "queued"
    slurm_job_id: int | None = None

    events: list[tuple[int, str, dict[str, Any]]] = field(default_factory=list)
    new_event: asyncio.Event = field(default_factory=asyncio.Event)
    loop: asyncio.AbstractEventLoop | None = None

    pending_question: dict[str, Any] | None = None
    _answers: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    _verdict: asyncio.Future | None = None

    # -- event log ---------------------------------------------------------------------

    def emit(self, event: str, data: dict[str, Any]) -> None:
        """Append to the event log and wake SSE consumers; safe from any thread."""
        self.events.append((len(self.events) + 1, event, data))
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if self.loop is None or running is self.loop:
            self.new_event.set()
        else:
            self.loop.call_soon_threadsafe(self.new_event.set)

    def set_status(self, status: str) -> None:
        self.status = status
        self.emit("status", {"status": status})

    # -- bridge: runner side -----------------------------------------------------------

    def publish_question(self, question: dict[str, Any]) -> None:
        self.pending_question = question
        self.emit("question", question)

    def publish_auto_answer(self, question: dict[str, Any], value: Any) -> None:
        self.emit("auto-answered", {"question": question, "value": value})

    async def await_answer(self, wait: float) -> tuple[bool, Any]:
        """Long-poll for the browser's next answer; returns (available, value)."""
        try:
            value = await asyncio.wait_for(self._answers.get(), timeout=wait)
        except asyncio.TimeoutError:
            return False, None
        return True, value

    def publish_verdict(self, accepted: bool, message: str | None, value: Any) -> None:
        if accepted:
            question = self.pending_question or {}
            self.pending_question = None
            self.emit("answer-accepted", {"question": question, "value": value})
        else:
            variablename = (self.pending_question or {}).get("variablename")
            self.emit("answer-rejected", {"variablename": variablename, "message": message})
        if self._verdict is not None and not self._verdict.done():
            self._verdict.set_result({"accepted": accepted, "message": message})
        self._verdict = None

    def finish(self, status: str, payload: dict[str, Any]) -> None:
        self.status = status
        self.emit("completed" if status == "completed" else "failed", payload)

    # -- bridge: browser side ----------------------------------------------------------

    async def submit_answer(self, value: Any) -> dict[str, Any]:
        """Hand an answer to the runner and await its validation verdict."""
        loop = asyncio.get_running_loop()
        self._verdict = loop.create_future()
        await self._answers.put(value)
        return await asyncio.wait_for(self._verdict, timeout=300)


class SessionStore:
    """In-memory session registry (one Form Runner instance per cluster)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        self._sessions[session.id] = session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)


store = SessionStore()
