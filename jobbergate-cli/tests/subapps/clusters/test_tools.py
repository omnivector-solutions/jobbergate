import json
from datetime import datetime

import httpx
import plummet
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ClusterCacheData, JobbergateContext
from jobbergate_cli.subapps.clusters.tools import (
    get_client_ids,
    load_clusters_from_cache,
    pull_client_ids_from_api,
    save_clusters_to_cache,
)


@pytest.fixture
def dummy_domain():
    return "https://dummy.com"


@pytest.fixture
def dummy_context(dummy_domain):
    return JobbergateContext(
        persona=None,
        client=httpx.Client(base_url=dummy_domain, headers={"Authorization": "Bearer XXXXXXXX"}),
    )


def test_pull_client_ids_from_api__success(respx_mock, dummy_domain, dummy_context):
    clusters_route = respx_mock.post(f"{dummy_domain}/cluster/graphql/query")
    clusters_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                data=dict(
                    cluster=[
                        dict(clientId="cluster1"),
                        dict(clientId="cluster2"),
                        dict(clientId="cluster3"),
                    ],
                ),
            ),
        ),
    )

    assert pull_client_ids_from_api(dummy_context) == ["cluster1", "cluster2", "cluster3"]


def test_pull_client_ids_from_api__raises_abort_on_non_200(respx_mock, dummy_domain, dummy_context):
    clusters_route = respx_mock.post(f"{dummy_domain}/cluster/graphql/query")
    clusters_route.mock(
        return_value=httpx.Response(
            httpx.codes.BAD_REQUEST,
        ),
    )

    with pytest.raises(Abort, match="There was a problem retrieving registered clusters"):
        pull_client_ids_from_api(dummy_context)


def test_pull_client_ids_from_api__raises_abort_on_malformed_response(respx_mock, dummy_domain, dummy_context):
    clusters_route = respx_mock.post(f"{dummy_domain}/cluster/graphql/query")
    clusters_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(bad="data"),
        ),
    )

    with pytest.raises(Abort, match="Couldn't unpack cluster names"):
        pull_client_ids_from_api(dummy_context)


def test_save_clusters_to_cache(tmp_path, tweak_settings):
    cluster_cache_path = tmp_path / "clusters.json"
    with tweak_settings(JOBBERGATE_CLUSTER_LIST_PATH=cluster_cache_path):
        with plummet.frozen_time("2022-05-13 16:56:00"):
            save_clusters_to_cache(["cluster1", "cluster2", "cluster3"])

    cache_data = ClusterCacheData(**json.loads(cluster_cache_path.read_text()))
    assert cache_data.client_ids == ["cluster1", "cluster2", "cluster3"]
    assert plummet.moments_match(cache_data.updated_at, "2022-05-13 16:56:00")


def test_load_clusters_from_cache__success(tmp_path, tweak_settings):
    cluster_cache_path = tmp_path / "clusters.json"
    with tweak_settings(JOBBERGATE_CLUSTER_LIST_PATH=cluster_cache_path, JOBBERGATE_CLUSTER_CACHE_LIFETIME=5):
        with plummet.frozen_time("2022-05-13 16:56:00"):
            cache_data = ClusterCacheData(
                updated_at=datetime.utcnow(),
                client_ids=["cluster1", "cluster2", "cluster3"],
            )
            cluster_cache_path.write_text(cache_data.model_dump_json())

            assert load_clusters_from_cache() == ["cluster1", "cluster2", "cluster3"]


def test_load_clusters_from_cache__returns_None_if_cache_is_expired(tmp_path, tweak_settings):
    cluster_cache_path = tmp_path / "clusters.json"
    with tweak_settings(JOBBERGATE_CLUSTER_LIST_PATH=cluster_cache_path, JOBBERGATE_CLUSTER_CACHE_LIFETIME=5):
        with plummet.frozen_time("2022-05-13 16:56:00"):
            cache_data = ClusterCacheData(
                updated_at=datetime.utcnow(),
                client_ids=["cluster1", "cluster2", "cluster3"],
            )
            cluster_cache_path.write_text(cache_data.model_dump_json())

        with plummet.frozen_time("2022-05-13 16:56:06"):
            assert load_clusters_from_cache() is None


def test_load_clusters_from_cache__returns_None_if_cache_is_invalid(tmp_path, tweak_settings):
    cluster_cache_path = tmp_path / "clusters.json"
    with tweak_settings(JOBBERGATE_CLUSTER_LIST_PATH=cluster_cache_path, JOBBERGATE_CLUSTER_CACHE_LIFETIME=5):
        cluster_cache_path.write_text("BAD DATA")
        assert load_clusters_from_cache() is None


def test_get_client_ids__pulls_from_api_if_no_cache_available(
    tmp_path, mocker, respx_mock, dummy_domain, dummy_context, tweak_settings
):
    """

    Also assert that a new cache file was created.
    """
    mocker.patch("jobbergate_cli.subapps.clusters.tools.load_clusters_from_cache", return_value=None)
    clusters_route = respx_mock.post(f"{dummy_domain}/cluster/graphql/query")
    clusters_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                data=dict(
                    cluster=[
                        dict(clientId="cluster1"),
                        dict(clientId="cluster2"),
                        dict(clientId="cluster3"),
                    ],
                ),
            ),
        ),
    )

    dummy_cache_path = tmp_path / "cluster-names.json"
    with tweak_settings(JOBBERGATE_CLUSTER_LIST_PATH=dummy_cache_path):
        with plummet.frozen_time("2022-05-16 15:38:00"):
            assert get_client_ids(dummy_context) == ["cluster1", "cluster2", "cluster3"]
    assert clusters_route.called
    cached_data = json.loads(dummy_cache_path.read_text())
    assert cached_data["client_ids"] == ["cluster1", "cluster2", "cluster3"]
    assert plummet.moments_match(cached_data["updated_at"], "2022-05-16 15:38:00")


def test_get_client_ids__loads_from_cache_when_available(mocker, respx_mock, dummy_domain, dummy_context):
    mocker.patch("jobbergate_cli.subapps.clusters.tools.load_clusters_from_cache", return_value=None)
    clusters_route = respx_mock.post(f"{dummy_domain}/cluster/graphql/query")
    clusters_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                data=dict(
                    cluster=[
                        dict(clientId="cluster1"),
                        dict(clientId="cluster2"),
                        dict(clientId="cluster3"),
                    ],
                ),
            ),
        ),
    )

    assert get_client_ids(dummy_context) == ["cluster1", "cluster2", "cluster3"]
    assert clusters_route.called
