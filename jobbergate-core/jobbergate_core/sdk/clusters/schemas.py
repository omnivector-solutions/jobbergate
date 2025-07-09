from pydantic import BaseModel

from jobbergate_core.sdk.schemas import PydanticDateTime


class ClusterStatusView(BaseModel):
    """
    Describes the status of a cluster.
    """

    client_id: str
    created_at: PydanticDateTime
    updated_at: PydanticDateTime
    last_reported: PydanticDateTime
    interval: int
    is_healthy: bool
