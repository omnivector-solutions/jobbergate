import pydantic
import pytest
import respx
from httpx import codes, Response
from polyfactory.factories.pydantic_factory import ModelFactory

from jobbergate_core.sdk.clusters.app import ClusterStatus
from jobbergate_core.sdk.clusters.schemas import ClusterStatusView
from jobbergate_core.sdk.schemas import PydanticDateTime
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"

ModelFactory.add_provider(PydanticDateTime, lambda: ModelFactory.__faker__.date_time())


class ClusterStatusViewFactory(ModelFactory[ClusterStatusView]):
    """Factory for generating test data based on ClusterStatusView objects."""

    __model__ = ClusterStatusView


class TestClusterStatus:
    clusters = ClusterStatus(client=Client(base_url=BASE_URL))

    def test_get_one(self, respx_mock) -> None:
        """Test the get_one method of ClusterStatus."""
        response_data = ClusterStatusViewFactory.build()
        client_id = response_data.client_id

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.get(f"/jobbergate/cluster/status/{client_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )
            result = self.clusters.get_one(client_id)

        assert route.call_count == 1
        assert result == response_data

    @pytest.mark.parametrize("client_id", [None, 10, True, object()])
    def test_get_one__bad_arguments(self, respx_mock, client_id) -> None:
        """Test the get_one method of ClusterStatus."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=True),
            pytest.raises(pydantic.ValidationError),
        ):
            route = respx_mock.get(f"/jobbergate/cluster/status/{client_id}")
            self.clusters.get_one(client_id)

        assert route.call_count == 0

    def test_get_one_request_error(self, respx_mock, faker) -> None:
        """Test the get_one method of ClusterStatus with a request error."""
        client_id = faker.uuid4()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/cluster/status/{client_id}").mock(
                return_value=Response(codes.INTERNAL_SERVER_ERROR)
            )
            self.clusters.get_one(client_id)

        assert route.call_count == 1

    def test_get_one_validation_error(self, respx_mock, faker) -> None:
        """Test the get_one method of ClusterStatus with a validation error."""
        client_id = faker.uuid4()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/cluster/status/{client_id}").mock(
                return_value=Response(codes.OK, json={"invalid": "data"})
            )
            self.clusters.get_one(client_id)

        assert route.call_count == 1

    def test_list(self, respx_mock, wrap_items_on_paged_response) -> None:
        """Test the list method of ClusterStatus."""
        response_data = wrap_items_on_paged_response(items=ClusterStatusViewFactory.batch(10))
        list_kwargs = {
            "size": response_data.size,
            "page": response_data.page,
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True):
            route = respx_mock.get("/jobbergate/cluster/status", params=list_kwargs).mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json()),
            )
            result = self.clusters.get_list(**list_kwargs)

        assert route.call_count == 1
        assert response_data == result

    def test_list_request_error(self, respx_mock) -> None:
        """Test the list method of ClusterStatus with a request error."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get("/jobbergate/cluster/status").mock(
                return_value=Response(codes.INTERNAL_SERVER_ERROR)
            )
            self.clusters.get_list()

        assert route.call_count == 1

    def test_list_validation_error(self, respx_mock) -> None:
        """Test the list method of ClusterStatus with a validation error."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True),
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get("/jobbergate/cluster/status").mock(
                return_value=Response(codes.OK, json={"invalid": "data"})
            )
            self.clusters.get_list()

        assert route.call_count == 1
