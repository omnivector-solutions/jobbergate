from datetime import datetime, timezone

import pytest
from fastapi import status
from httpx import AsyncClient

from jobbergate_api.analytics.route import _bucket_count
from jobbergate_api.analytics.schemas import ReportInterval
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus, SlurmJobState
from jobbergate_api.apps.permissions import Permissions


def test_bucket_count_counts_distinct_buckets_across_boundaries():
    start = datetime(2026, 9, 8, 23, 30, tzinfo=timezone.utc)
    end = datetime(2026, 9, 9, 0, 10, tzinfo=timezone.utc)
    assert _bucket_count(start, end, ReportInterval.HOUR) == 2
    assert _bucket_count(start, end, ReportInterval.DAY) == 2
    # 2026-09-08 is a Tuesday; the Monday after it starts a new date_trunc week bucket.
    assert _bucket_count(start, datetime(2026, 9, 13, tzinfo=timezone.utc), ReportInterval.WEEK) == 1
    assert _bucket_count(start, datetime(2026, 9, 14, tzinfo=timezone.utc), ReportInterval.WEEK) == 2
    assert (
        _bucket_count(
            datetime(2026, 9, 8, tzinfo=timezone.utc), datetime(2026, 9, 10, tzinfo=timezone.utc), ReportInterval.DAY
        )
        == 3
    )


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_require_authentication(client: AsyncClient, path: str):
    response = await client.get(f"/jobbergate/analytics/{path}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_require_metrics_permission(
    client: AsyncClient, inject_security_header, tester_email: str, path: str
):
    inject_security_header(tester_email, Permissions.JOB_SUBMISSIONS_READ)

    response = await client.get(f"/jobbergate/analytics/{path}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_reject_inverted_time_range(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/analytics/{path}",
        params={"start_time": "2026-09-08T12:00:00Z", "end_time": "2026-09-08T11:00:00Z"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "End time must be greater than the start time."


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_reject_windows_with_too_many_buckets(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/analytics/{path}",
        params={"start_time": "2024-09-08T00:00:00Z", "end_time": "2026-09-08T00:00:00Z", "interval": "hour"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Use a coarser interval or a shorter time window." in response.json()["detail"]


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_accept_long_windows_with_coarse_buckets(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/analytics/{path}",
        params={"start_time": "2024-09-08T00:00:00Z", "end_time": "2026-09-08T00:00:00Z", "interval": "day"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_bucket_limit_is_configurable(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session, tweak_settings
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    with tweak_settings(ANALYTICS_MAX_BUCKETS=10):
        response = await client.get(
            f"/jobbergate/analytics/{path}",
            params={"start_time": "2026-09-01T00:00:00Z", "end_time": "2026-09-12T00:00:00Z", "interval": "day"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeding the maximum of 10" in response.json()["detail"]


@pytest.mark.parametrize("path", ("templates", "submissions"))
async def test_analytics_routes_return_empty_report_without_data(
    client: AsyncClient, inject_security_header, tester_email: str, path: str, synth_session
):
    inject_security_header(tester_email, Permissions.METRICS_READ)

    response = await client.get(
        f"/jobbergate/analytics/{path}",
        params={"start_time": "2026-09-08T00:00:00Z", "end_time": "2026-09-09T00:00:00Z"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["start_time"] == "2026-09-08T00:00:00Z"
    assert data["end_time"] == "2026-09-09T00:00:00Z"
    assert data["interval"] == "day"


async def test_template_usage_report_buckets_by_interval(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    template = await synth_services.crud.template.create(
        name="analytics-template",
        description="Analytics template",
        owner_email=tester_email,
        is_archived=False,
        identifier="template-a",
    )
    script_a = await synth_services.crud.job_script.create(
        name="analytics-script-a",
        description="Analytics script A",
        owner_email=tester_email,
        is_archived=False,
        parent_template_id=template.id,
    )
    script_b = await synth_services.crud.job_script.create(
        name="analytics-script-b",
        description="Analytics script B",
        owner_email=tester_email,
        is_archived=False,
        parent_template_id=template.id,
    )
    for name, script_id, client_id, created_at in (
        ("analytics-submission-a", script_a.id, "cluster-a", datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc)),
        ("analytics-submission-b", script_b.id, "cluster-a", datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)),
        ("analytics-submission-c", script_a.id, "cluster-b", datetime(2026, 9, 9, 9, 30, tzinfo=timezone.utc)),
        # Outside the requested window; must be excluded.
        ("analytics-submission-d", script_a.id, "cluster-a", datetime(2026, 9, 20, 9, 30, tzinfo=timezone.utc)),
    ):
        await synth_services.crud.job_submission.create(
            name=name,
            description="Analytics submission",
            owner_email=tester_email,
            is_archived=False,
            status=JobSubmissionStatus.CREATED,
            sbatch_arguments=[],
            job_script_id=script_id,
            client_id=client_id,
            created_at=created_at,
        )

    response = await client.get(
        "/jobbergate/analytics/templates",
        params={"start_time": "2026-09-08T00:00:00Z", "end_time": "2026-09-10T00:00:00Z", "interval": "day"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["interval"] == "day"
    assert data["items"] == [
        {
            "bucket": "2026-09-08T00:00:00Z",
            "client_id": "cluster-a",
            "template_id": template.id,
            "template_identifier": "template-a",
            "count": 2,
        },
        {
            "bucket": "2026-09-09T00:00:00Z",
            "client_id": "cluster-b",
            "template_id": template.id,
            "template_identifier": "template-a",
            "count": 1,
        },
    ]


async def test_template_usage_report_uses_template_id_fallback(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    template = await synth_services.crud.template.create(
        name="analytics-template-no-identifier",
        description="Analytics template without identifier",
        owner_email=tester_email,
        is_archived=False,
    )
    script = await synth_services.crud.job_script.create(
        name="analytics-script",
        description="Analytics script",
        owner_email=tester_email,
        is_archived=False,
        parent_template_id=template.id,
    )
    await synth_services.crud.job_submission.create(
        name="analytics-submission",
        description="Analytics submission",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        job_script_id=script.id,
        client_id="cluster-a",
        created_at=datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/jobbergate/analytics/templates",
        params={"start_time": "2026-09-08T00:00:00Z", "end_time": "2026-09-09T00:00:00Z"},
    )

    assert response.status_code == status.HTTP_200_OK
    (item,) = response.json()["items"]
    assert item["template_id"] == template.id
    assert item["template_identifier"] == f"template_id:{template.id}"


async def test_template_usage_report_counts_submissions_without_template_as_unknown(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    """A deleted job script or template must not drop submissions from the report (SET NULL FKs)."""
    inject_security_header(tester_email, Permissions.METRICS_READ)
    # Submission whose job script is gone (job_script_id SET NULL).
    await synth_services.crud.job_submission.create(
        name="analytics-submission-orphan",
        description="Analytics submission without a job script",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        client_id="cluster-a",
        created_at=datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc),
    )
    # Submission whose job script lost its template (parent_template_id SET NULL).
    script = await synth_services.crud.job_script.create(
        name="analytics-script-orphan",
        description="Analytics script without a template",
        owner_email=tester_email,
        is_archived=False,
    )
    await synth_services.crud.job_submission.create(
        name="analytics-submission-orphan-template",
        description="Analytics submission whose script has no template",
        owner_email=tester_email,
        is_archived=False,
        status=JobSubmissionStatus.CREATED,
        sbatch_arguments=[],
        job_script_id=script.id,
        client_id="cluster-a",
        created_at=datetime(2026, 9, 8, 13, 15, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/jobbergate/analytics/templates",
        params={"start_time": "2026-09-08T00:00:00Z", "end_time": "2026-09-09T00:00:00Z"},
    )

    assert response.status_code == status.HTTP_200_OK
    (item,) = response.json()["items"]
    assert item["template_id"] is None
    assert item["template_identifier"] == "unknown"
    assert item["count"] == 2


async def test_submission_status_report_groups_by_status(
    client: AsyncClient,
    inject_security_header,
    tester_email: str,
    synth_services,
):
    inject_security_header(tester_email, Permissions.METRICS_READ)
    for name, client_id, submission_status, slurm_job_state in (
        ("analytics-submission-running-1", "cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING),
        ("analytics-submission-running-2", "cluster-a", JobSubmissionStatus.SUBMITTED, SlurmJobState.RUNNING),
        ("analytics-submission-created", "cluster-b", JobSubmissionStatus.CREATED, None),
    ):
        await synth_services.crud.job_submission.create(
            name=name,
            description="Analytics submission",
            owner_email=tester_email,
            is_archived=False,
            sbatch_arguments=[],
            client_id=client_id,
            status=submission_status,
            slurm_job_state=slurm_job_state,
            created_at=datetime(2026, 9, 8, 12, 15, tzinfo=timezone.utc),
        )

    response = await client.get(
        "/jobbergate/analytics/submissions",
        params={"start_time": "2026-09-08T00:00:00Z", "end_time": "2026-09-09T00:00:00Z", "interval": "day"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == [
        {
            "bucket": "2026-09-08T00:00:00Z",
            "client_id": "cluster-a",
            "status": "SUBMITTED",
            "slurm_job_state": "RUNNING",
            "count": 2,
        },
        {
            "bucket": "2026-09-08T00:00:00Z",
            "client_id": "cluster-b",
            "status": "CREATED",
            "slurm_job_state": None,
            "count": 1,
        },
    ]
