# Spec 2 — `/analytics/*` JSON endpoints (jobbergate-api)

## Goal

Additive JSON reporting endpoints over the same aggregation queries the shipped
`/metrics/*` endpoints run, consumable by Grafana Infinity, the CLI, and any future
archive job. The Prometheus-format `/metrics/*` endpoints are **not** touched.

## Endpoints

New package `jobbergate_api/analytics/` (`route.py`, `schemas.py`), router mounted in
`main.py` with prefix `/analytics`, tag `Analytics`, guarded by the same dependency as
metrics: `secure_services(Permissions.ADMIN, Permissions.METRICS_READ, commit=False)`.

### `GET /jobbergate/analytics/templates`

Query params (shared with `/metrics/*` semantics):

- `start_time` (optional datetime, UTC assumed when naive) — inclusive, on
  `job_submissions.created_at`; defaults to one day before `end_time`.
- `end_time` (optional datetime) — inclusive; defaults to now.
- `interval` (`hour|day|week`, reusing `MetricsInterval`) — **default `day`** (JSON
  reports span days-to-months; `hour` stays the default only on the scrape endpoints).
- 400 when `end_time < start_time` (same `_window` logic as metrics; factor the helper
  into `jobbergate_api/utils/` or duplicate minimally — prefer a shared
  `jobbergate_api.utils.time`-adjacent helper `resolve_window`).

Response `TemplateUsageReport`:

```json
{
  "start_time": "2026-07-27T00:00:00Z",
  "end_time": "2026-10-27T00:00:00Z",
  "interval": "day",
  "items": [
    {"bucket": "2026-10-01T00:00:00Z", "client_id": "cluster-a",
     "template_identifier": "fem-basic", "count": 12}
  ]
}
```

`template_identifier` uses the `template_id:<id>` fallback when the template has no
identifier, matching the metrics labels.

### `GET /jobbergate/analytics/submissions`

Same params. Response `SubmissionStatusReport` rows:
`{bucket, client_id, status, slurm_job_state, count}` with `slurm_job_state: null`
preserved as JSON null (consumers decide how to label it; the Prometheus endpoint's
`"unknown"` is an exposition-format constraint that does not apply here).

## Schemas

`analytics/schemas.py`: `TemplateUsageRow`, `SubmissionStatusRow`,
`TemplateUsageReport`, `SubmissionStatusReport` (pydantic). Buckets serialize as ISO
datetimes.

## Notes

- Queries are the same `date_trunc`/`group_by` selects as `metrics/route.py`; rows map
  straight into the pydantic rows.
- Data is bounded by the database retention window — exact within it. That is by
  design (the TSDB keeps longer approximate history via the scraped gauges).
- Changelog fragment: `changes/api/+analytics-endpoints.added.md`.

## Tests (`jobbergate-api/tests/test_analytics.py`)

- 401 without token, 403 without `METRICS_READ`/`ADMIN`, for both paths.
- 400 when `end_time < start_time`.
- Template report: seed templates/scripts/submissions with explicit `created_at`,
  assert bucketing by `interval=day` and the identifier fallback.
- Submission report: assert grouping by status/slurm state and `null` slurm state.
- Window filtering: submissions outside `[start_time, end_time]` are excluded.
- Empty DB → `items: []`, echoed window/interval.
