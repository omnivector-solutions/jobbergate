"""
Provide tool functions for working with Cluster data
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, cast

from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import ClusterCacheData, JobbergateContext
from jobbergate_cli.text_tools import conjoin


def pull_client_ids_from_api(ctx: JobbergateContext) -> List[str]:
    assert ctx.client is not None

    response_data = cast(
        Dict,
        make_request(
            ctx.client,
            "/cluster/graphql/query",
            "POST",
            expected_status=200,
            abort_message="There was a problem retrieving registered clusters from the Cluster API",
            abort_subject="COULD NOT RETRIEVE CLUSTERS",
            support=True,
            json=dict(
                query="query {cluster{clientId}}",
                variables=dict(),
            ),
        ),
    )

    try:
        client_ids = [e["clientId"] for e in response_data["data"]["cluster"]]
    except Exception as err:
        raise Abort(
            "Couldn't unpack cluster names from Cluster API response",
            subject="COULD NOT RETRIEVE CLUSTERS",
            support=True,
            original_error=err,
            log_message=f"Failed to unpack data from cluster-api: {response_data}",
        )
    return client_ids


def save_clusters_to_cache(client_ids: List[str]):

    # Make static type checkers happy
    assert settings.JOBBERGATE_CLUSTER_LIST_PATH is not None

    cache_data = ClusterCacheData(
        updated_at=datetime.utcnow(),
        client_ids=client_ids,
    )

    logger.debug(f"Caching cluster info at {settings.JOBBERGATE_CLUSTER_LIST_PATH}")
    settings.JOBBERGATE_CLUSTER_LIST_PATH.write_text(cache_data.json())


def load_clusters_from_cache() -> Optional[List[str]]:

    # Make static type checkers happy
    assert settings.JOBBERGATE_CLUSTER_LIST_PATH is not None

    try:
        cache_data = ClusterCacheData(**json.loads(settings.JOBBERGATE_CLUSTER_LIST_PATH.read_text()))
    except Exception as err:
        logger.warning(f"Couldn't load cluster data from cache: {err}")
        return None

    if datetime.utcnow().timestamp() - cache_data.updated_at.timestamp() > settings.JOBBERGATE_CLUSTER_CACHE_LIFETIME:
        logger.warning("Cached cluster data is expired")
        return None

    return cache_data.client_ids


def get_client_ids(ctx: JobbergateContext) -> List[str]:
    assert ctx.client is not None

    client_ids = load_clusters_from_cache()
    if client_ids is None:
        client_ids = pull_client_ids_from_api(ctx)
        save_clusters_to_cache(client_ids)

    return client_ids


def validate_client_id(ctx: JobbergateContext, client_id: str):
    client_ids = get_client_ids(ctx)
    Abort.require_condition(
        client_id in client_ids,
        conjoin(
            """
            The supplied cluster name was not found in the list of available clusters.

            Please select one of:
            """,
            *client_ids,
        ),
        raise_kwargs=dict(
            subject="Invalid cluster name",
            support=True,
        ),
    )
