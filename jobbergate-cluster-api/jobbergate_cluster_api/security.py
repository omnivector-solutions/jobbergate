"""
Auth guard for the cluster API.

Reuses the same Armasec/OIDC validation as the cloud jobbergate-api. Sessions are
locked down with the existing job-script creation permissions — creating a session
is, functionally, creating a job script — so no new realm roles are required for the
PoC. The guard mirrors the cloud API's route exactly: ``jobbergate:admin`` OR
``jobbergate:job-scripts:create`` (PermissionMode.SOME).
"""

from armasec import Armasec
from armasec.token_security import PermissionMode
from fastapi import HTTPException, Request, status
from loguru import logger

from jobbergate_cluster_api.config import settings

SESSION_PERMISSIONS = ("jobbergate:admin", "jobbergate:job-scripts:create")

guard = Armasec(
    domain=settings.ARMASEC_DOMAIN,
    debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
    use_https=settings.ARMASEC_USE_HTTPS,
    ignore_audience=True,
)


lockdown_session = guard.lockdown(*SESSION_PERMISSIONS, permission_mode=PermissionMode.SOME)


def get_bearer_token(request: Request) -> str:
    """
    Extract the raw Bearer token from the request so it can be seeded into the
    session's token cache (Armasec only exposes the decoded payload).
    """
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    return token.strip()
