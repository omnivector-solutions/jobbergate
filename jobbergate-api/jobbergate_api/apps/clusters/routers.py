"""Cluster status API endpoints."""

from fastapi import APIRouter, Depends, Query
from fastapi import Response as FastAPIResponse
from fastapi import status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from loguru import logger
from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import select

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.apps.clusters.schemas import ClusterStatusView
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.storage import SecureSession, secure_session

router = APIRouter(prefix="/clusters", tags=["Cluster Status"])


@router.put(
    "/status",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoints to accept a status check from the agent on the clusters.",
)
async def report_cluster_status(
    interval: int = Query(description="The interval in seconds between pings.", gt=0),
    secure_session: SecureSession = Depends(
        secure_session(Permissions.CLUSTERS_UPDATE, ensure_client_id=True)
    ),
):
    """
    Report the status of the cluster.
    """
    logger.debug(
        "Got status report from client_id={}, another ping is expected in {} seconds",
        secure_session.identity_payload.client_id,
        interval,
    )
    instance = ClusterStatus(
        client_id=secure_session.identity_payload.client_id,
        interval=interval,
        last_reported=PendulumDateTime.utcnow(),
    )
    await secure_session.session.merge(instance)

    return FastAPIResponse(status_code=status.HTTP_202_ACCEPTED)


@router.get(
    "/status",
    description="Endpoint to get the status of the cluster.",
    response_model=Page[ClusterStatusView],
)
async def get_cluster_status(
    secure_session: SecureSession = Depends(secure_session(Permissions.CLUSTERS_READ, commit=False)),
):
    """
    Get the status of the cluster.
    """
    logger.debug("Getting list of cluster statuses")
    query = select(ClusterStatus).order_by(ClusterStatus.client_id)
    return await paginate(secure_session.session, query)
