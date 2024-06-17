"""Schema definitions for the cluster app."""

from pydantic import BaseModel, ConfigDict

from jobbergate_api.apps.schemas import PydanticDateTime
from jobbergate_api.meta_mapper import MetaField, MetaMapper

cluster_status_meta_mapper = MetaMapper(
    client_id=MetaField(
        description="The client_id of the cluster where this agent is reporting status from",
        example="mega-cluster-1",
    ),
    created_at=MetaField(
        description="The timestamp for when this entry was created",
        example="2023-08-18T13:55:37.172285",
    ),
    updated_at=MetaField(
        description="The timestamp for when this entry was last updated",
        example="2023-08-18T13:55:37.172285",
    ),
    last_reported=MetaField(
        description="The timestamp for when the agent on the cluster last reported its status",
        example="2023-08-18T13:55:37.172285",
    ),
    interval=MetaField(
        description="The expected interval in seconds between pings from the agent",
        example=60,
    ),
    is_healthy=MetaField(
        description="A boolean indicating if the cluster is healthy based on the last_reported time",
        example=True,
    ),
)


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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=cluster_status_meta_mapper,
    )
