"""
SDK module to interact with cluster status API.
"""

from typing import ClassVar, Type

from httpx import codes
from pydantic import ConfigDict, PositiveInt, validate_call
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.clusters.schemas import ClusterStatusView
from jobbergate_core.sdk.schemas import ListResponseEnvelope
from jobbergate_core.sdk.utils import filter_null_out
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class ClusterStatus:
    """
    SDK class to interact with the cluster status API.
    """

    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    base_path: ClassVar[str] = "/jobbergate/cluster/status"

    @validate_call
    def get_list(self, size: PositiveInt = 50, page: PositiveInt = 1) -> ListResponseEnvelope[ClusterStatusView]:
        """
        Get a list of cluster statuses.

        Args:
            size: The number of items to return in the response.
            page: The page number to return.

        Returns:
            A list of cluster statuses.
        """
        params = filter_null_out(dict(size=size, page=page))
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=self.base_path,
                method="GET",
                request_kwargs=dict(params=params),
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(ListResponseEnvelope[ClusterStatusView])
        )

    @validate_call
    def get_one(self, client_id: str) -> ClusterStatusView:
        """
        Get a specific cluster status.

        Args:
            client_id: The client_id of the cluster to get the status for.

        Returns:
            The status of the cluster.
        """
        return (
            self.request_handler_cls(
                client=self.client,
                url_path=f"{self.base_path}/{client_id}",
                method="GET",
            )
            .raise_for_status()
            .check_status_code(codes.OK)
            .to_model(ClusterStatusView)
        )
