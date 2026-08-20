"""
Armasec resources locking the Form Runner public endpoints.

Takes after ``jobbergate_api.security``: the same Keycloak domain issues the tokens, the same
permission scopes gate access, and the identity (``sub``/``email``) extracted here is what binds
a session to its owner.
"""

from typing import Annotated

from armasec import Armasec, TokenPayload
from armasec.token_security import PermissionMode
from fastapi import Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from jobbergate_form_runner.config import settings

guard = Armasec(
    domain=settings.ARMASEC_DOMAIN,
    debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
    use_https=settings.ARMASEC_USE_HTTPS,
    ignore_audience=True,
)

ADMIN = "jobbergate:admin"
JOB_SCRIPTS_CREATE = "jobbergate:job-scripts:create"
JOB_SUBMISSIONS_CREATE = "jobbergate:job-submissions:create"

# Interacting with an owned session (answers, events, snapshot, cancel) is read-level;
# the write scopes a session ultimately needs (create job scripts / submissions) are
# enforced explicitly at session creation via Identity.require_permissions.
SESSION_SCOPES = (
    ADMIN,
    JOB_SCRIPTS_CREATE,
    "jobbergate:job-scripts:read",
    "jobbergate:job-submissions:read",
    "jobbergate:job-templates:read",
)


class Identity(BaseModel):
    """The identity of the caller, extracted from the access token."""

    sub: str
    email: str | None = None
    permissions: list[str] = []

    def require_permissions(self, *scopes: str) -> None:
        """Ensure the token carries every given scope (admin bypasses)."""
        if ADMIN in self.permissions:
            return
        missing = [scope for scope in scopes if scope not in self.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access token is missing required permissions: {', '.join(missing)}",
            )


_session_security = guard.lockdown(*SESSION_SCOPES, permission_mode=PermissionMode.SOME)


def _extract_identity(token_payload: TokenPayload) -> Identity:
    payload = token_payload.model_dump()
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access token does not contain sub")
    return Identity(sub=sub, email=payload.get("email"), permissions=list(payload.get("permissions") or []))


def locked_identity(
    token_payload: Annotated[TokenPayload, Depends(_session_security)],
) -> Identity:
    """Lock down a route and extract the caller's identity."""
    return _extract_identity(token_payload)


async def identify_request(request) -> Identity:
    """Validate the request's bearer token imperatively (for routes with dual auth)."""
    return _extract_identity(await _session_security(request))
