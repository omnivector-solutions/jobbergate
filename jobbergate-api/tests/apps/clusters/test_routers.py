from jobbergate_api.apps.permissions import Permissions
from fastapi import status
from jobbergate_api.apps.clusters.models import ClusterStatus
from sqlalchemy import select
import pytest
import pendulum


class TestPutClusterStatus:

    async def test_report_cluster_status__health(self, client, inject_security_header, synth_session):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.JOB_SUBMISSIONS_EDIT,
            client_id=client_id,
        )

        interval = 60
        response = await client.put("/jobbergate/clusters/status", params={"interval": interval})

        assert response.status_code == status.HTTP_202_ACCEPTED

        query = select(ClusterStatus).filter(ClusterStatus.client_id == client_id)
        instance = (await synth_session.execute(query)).unique().scalar_one()

        assert instance.client_id == client_id
        assert instance.interval == interval
        assert instance.is_health is True

    async def test_report_cluster_status__not_health(self, client, inject_security_header, synth_session):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.JOB_SUBMISSIONS_EDIT,
            client_id=client_id,
        )

        interval = 60

        with pendulum.test(pendulum.datetime(2023, 1, 1)):
            response = await client.put("/jobbergate/clusters/status", params={"interval": interval})
            assert response.status_code == status.HTTP_202_ACCEPTED

        with pendulum.test(pendulum.datetime(2023, 1, 1).add(seconds=interval + 1)):
            query = select(ClusterStatus).filter(ClusterStatus.client_id == client_id)
            instance = (await synth_session.execute(query)).unique().scalar_one()

            assert instance.client_id == client_id
            assert instance.interval == interval
            assert instance.is_health is False

    @pytest.mark.parametrize("interval", [0, -1, None])
    async def test_report__invalid_interval_raises_error(
        self, interval, client, inject_security_header, synth_session
    ):
        client_id = "dummy-client"
        inject_security_header(
            "who@cares.com",
            Permissions.JOB_SUBMISSIONS_EDIT,
            client_id=client_id,
        )

        response = await client.put("/jobbergate/clusters/status", params={"interval": interval})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_report_cluster_status__no_client_id(self, client, inject_security_header):

        inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_EDIT)

        response = await client.put("/jobbergate/clusters/status", params={"interval": 60})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_report_cluster_status__bad_permission(self, client, inject_security_header):

        inject_security_header("who@cares.com", client_id="dummy-client")

        response = await client.put("/jobbergate/clusters/status", params={"interval": 60})

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListClusterStatus:

    async def test_get_cluster_status__empty(
        self, client, inject_security_header, unpack_response, synth_session
    ):

        inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_VIEW)

        response = await client.get("/jobbergate/clusters/status")
        assert unpack_response(response, check_total=0, check_page=1, check_pages=0) == []

    async def test_get_cluster_status__list(
        self, client, inject_security_header, unpack_response, synth_session
    ):

        statuses = [
            ClusterStatus(client_id="client-1", interval=10, last_reported=pendulum.datetime(2023, 1, 1)),
            ClusterStatus(client_id="client-2", interval=20, last_reported=pendulum.datetime(2023, 1, 1)),
            ClusterStatus(client_id="client-3", interval=30, last_reported=pendulum.datetime(2022, 1, 1)),
        ]

        inject_security_header("who@cares.com", Permissions.JOB_SUBMISSIONS_VIEW)

        with pendulum.test(pendulum.datetime(2023, 1, 1)):
            synth_session.add_all(statuses)
            response = await client.get("/jobbergate/clusters/status")

        assert unpack_response(
            response, check_total=3, check_page=1, check_pages=1, key="client_id", sort=True
        ) == [s.client_id for s in statuses]

        assert unpack_response(response, key="is_health") == [True, True, False]

    async def test_get_cluster_status__bad_permission(self, client, inject_security_header, synth_session):

        inject_security_header("who@cares.com")

        response = await client.get("/jobbergate/clusters/status")

        assert response.status_code == status.HTTP_403_FORBIDDEN
