import pendulum
import pytest
from fastapi import status
from sqlalchemy import select

from jobbergate_api.apps.clusters.models import ClusterStatus
from jobbergate_api.apps.permissions import Permissions


class TestPutClusterStatus:
    async def test_report_cluster_status__create(self, client, inject_security_header, synth_session):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.CLUSTERS_UPDATE,
            client_id=client_id,
        )

        interval = 60
        now = pendulum.datetime(2023, 1, 1)
        with pendulum.travel_to(now, freeze=True):
            response = await client.put("/jobbergate/clusters/status", params={"interval": interval})

        assert response.status_code == status.HTTP_202_ACCEPTED

        query = select(ClusterStatus).filter(ClusterStatus.client_id == client_id)
        instance = (await synth_session.execute(query)).unique().scalar_one()

        assert instance.client_id == client_id
        assert instance.interval == interval
        assert instance.last_reported == now

    async def test_report_cluster_status__update(self, client, inject_security_header, synth_session):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.CLUSTERS_UPDATE,
            client_id=client_id,
        )

        original_time = pendulum.datetime(2023, 1, 1)
        original_interval = 60
        with pendulum.travel_to(original_time, freeze=True):
            response = await client.put("/jobbergate/clusters/status", params={"interval": original_interval})
            assert response.status_code == status.HTTP_202_ACCEPTED

        now = original_time.add(days=1)
        interval = original_interval * 2
        with pendulum.travel_to(now, freeze=True):
            response = await client.put("/jobbergate/clusters/status", params={"interval": interval})
            assert response.status_code == status.HTTP_202_ACCEPTED

        query = select(ClusterStatus).filter(ClusterStatus.client_id == client_id)
        instance = (await synth_session.execute(query)).unique().scalar_one()

        assert instance.client_id == client_id
        assert instance.interval == interval
        assert instance.last_reported == now

    @pytest.mark.parametrize("interval", [0, -1, None])
    async def test_report__invalid_interval_raises_error(
        self, interval, client, inject_security_header, synth_session
    ):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.CLUSTERS_UPDATE,
            client_id=client_id,
        )

        response = await client.put("/jobbergate/clusters/status", params={"interval": interval})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_report_cluster_status__no_client_id(self, client, inject_security_header):
        inject_security_header("who@cares.com", Permissions.CLUSTERS_UPDATE)

        response = await client.put("/jobbergate/clusters/status", params={"interval": 60})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_report_cluster_status__bad_permission(self, client, inject_security_header):
        inject_security_header("who@cares.com", client_id="dummy-client")

        response = await client.put("/jobbergate/clusters/status", params={"interval": 60})

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListClusterStatus:
    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.CLUSTERS_READ))
    async def test_get_cluster_status__empty(
        self, permission, client, inject_security_header, unpack_response, synth_session
    ):
        inject_security_header("who@cares.com", permission)

        response = await client.get("/jobbergate/clusters/status")
        assert unpack_response(response, check_total=0, check_page=1, check_pages=0) == []

    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.CLUSTERS_READ))
    async def test_get_cluster_status__list(
        self, permission, client, inject_security_header, unpack_response, synth_session
    ):
        statuses = [
            ClusterStatus(client_id="client-1", interval=10, last_reported=pendulum.datetime(2023, 1, 1)),
            ClusterStatus(client_id="client-2", interval=20, last_reported=pendulum.datetime(2023, 1, 1)),
            ClusterStatus(client_id="client-3", interval=30, last_reported=pendulum.datetime(2022, 1, 1)),
        ]

        inject_security_header("who@cares.com", permission)

        with pendulum.travel_to(pendulum.datetime(2023, 1, 1), freeze=True):
            synth_session.add_all(statuses)
            response = await client.get("/jobbergate/clusters/status")

        assert unpack_response(
            response, check_total=3, check_page=1, check_pages=1, key="client_id", sort=True
        ) == [s.client_id for s in statuses]

        assert unpack_response(response, key="is_healthy") == [True, True, False]

    async def test_get_cluster_status__bad_permission(self, client, inject_security_header, synth_session):
        inject_security_header("who@cares.com")

        response = await client.get("/jobbergate/clusters/status")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetClusterStatus:
    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.CLUSTERS_READ))
    @pytest.mark.parametrize("client_id", ("client-1", "client-2", "client-3"))
    async def test_get_cluster_status_by_client_id__not_found(
        self, permission, client_id, client, inject_security_header, synth_session
    ):
        inject_security_header("who@cares.com", permission)

        response = await client.get(f"/jobbergate/clusters/status/{client_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("permission", (Permissions.ADMIN, Permissions.CLUSTERS_READ))
    @pytest.mark.parametrize("client_id", ("client-1", "client-2", "client-3"))
    async def test_get_cluster_status_by_client_id__found(
        self, permission, client_id, client, inject_security_header, synth_session
    ):
        inject_security_header("who@cares.com", permission)

        cluster_status = ClusterStatus(
            client_id=client_id, interval=10, last_reported=pendulum.datetime(2023, 1, 1)
        )
        with pendulum.travel_to(pendulum.datetime(2023, 1, 1), freeze=True):
            synth_session.add(cluster_status)
            response = await client.get(f"/jobbergate/clusters/status/{client_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "client_id": client_id,
            "interval": 10,
            "last_reported": "2023-01-01T00:00:00Z",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "is_healthy": True,
        }
