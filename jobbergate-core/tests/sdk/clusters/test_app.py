from typing import Any

import pendulum
import pytest
import respx
from httpx import Response

from jobbergate_core.sdk.clusters.app import ClusterStatus
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"


def client_factory() -> Client:
    """Factory to create a Client instance."""
    return Client(base_url=BASE_URL)


def cluster_status_data_factory() -> dict[str, Any]:
    """Factory to create a detailed job script file data."""
    return {
        "client_id": "test",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
        "last_reported": "2021-01-01T00:00:00Z",
        "interval": 60,
        "is_healthy": True,
    }


def pack_on_paginated_response(data: dict[str, Any]) -> dict[str, Any]:
    """Pack data into a paginated response."""
    return {
        "items": [data],
        "total": 1,
        "page": 1,
        "size": 1,
        "pages": 1,
    }


class TestClusterStatus:
    clusters = ClusterStatus(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one(self, respx_mock) -> None:
        """Test the get_one method of ClusterStatus."""
        response_data = cluster_status_data_factory()
        route = respx_mock.get("/jobbergate/cluster/status/test").mock(return_value=Response(200, json=response_data))

        result = self.clusters.get_one("test")

        assert route.call_count == 1
        assert result.client_id == response_data["client_id"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.last_reported == pendulum.parse(response_data["last_reported"])
        assert result.interval == response_data["interval"]
        assert result.is_healthy == response_data["is_healthy"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_request_error(self, respx_mock) -> None:
        """Test the get_one method of ClusterStatus with a request error."""
        route = respx_mock.get("/jobbergate/cluster/status/test").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.clusters.get_one("test")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_validation_error(self, respx_mock) -> None:
        """Test the get_one method of ClusterStatus with a validation error."""
        route = respx_mock.get("/jobbergate/cluster/status/test").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.clusters.get_one("test")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list(self, respx_mock) -> None:
        """Test the list method of ClusterStatus."""
        response_data = pack_on_paginated_response(cluster_status_data_factory())
        list_kwargs = {
            "size": 100,
            "page": 10,
        }
        route = respx_mock.get("/jobbergate/cluster/status", params=list_kwargs).mock(
            return_value=Response(200, json=response_data),
        )

        result = self.clusters.get_list(**list_kwargs)

        assert route.call_count == 1
        assert len(result.items) == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_request_error(self, respx_mock) -> None:
        """Test the list method of ClusterStatus with a request error."""
        route = respx_mock.get("/jobbergate/cluster/status").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.clusters.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_validation_error(self, respx_mock) -> None:
        """Test the list method of ClusterStatus with a validation error."""
        route = respx_mock.get("/jobbergate/cluster/status").mock(return_value=Response(200, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.clusters.get_list()

        assert route.call_count == 1
