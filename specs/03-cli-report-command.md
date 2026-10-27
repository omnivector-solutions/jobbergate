# Spec 3 — `jobbergate report` CLI command

## Goal

On-demand access to the `/analytics/*` reports from the CLI, rendered as rich tables
(or raw JSON with the global `--raw` flag).

## Commands

New subapp `jobbergate_cli/subapps/report/app.py`, registered in `main.py` as
`app.add_typer(report_app, name="report")`.

- `jobbergate report templates [--start-time ...] [--end-time ...] [--interval hour|day|week]`
  → `GET /jobbergate/analytics/templates`
- `jobbergate report submissions [same options]`
  → `GET /jobbergate/analytics/submissions`

Options map 1:1 to the API query params and are omitted from the request when not
given, so API defaults (last day, `interval=day`) stay authoritative. `--interval`
is validated client-side via an enum mirroring the API's choices.

## Rendering

- `--raw` → `render_json(report["items"])`.
- Otherwise a `rich` table titled "Template usage" / "Submission statuses", one row per
  item, with the window echoed in the caption
  (`2026-07-27 → 2026-10-27, interval: day, total rows: N`).
- Empty `items` → `terminal_message("No data in the selected window", ...)`.

Responses are validated into pydantic models (`TemplateUsageReport`,
`SubmissionStatusReport`) added to `jobbergate_cli/schemas.py`, matching Spec 2.

## Errors

`make_request(..., expected_status=200)` handles 401/403/400 with the standard Abort
UX (403 → the user lacks `jobbergate:metrics:read`).

## Tests (`jobbergate-cli/tests/subapps/report/test_app.py`)

Use `make_test_app` + `respx` mocks like the other subapps:

- Each command hits the right path, forwards only the options that were set, and
  renders the mocked rows (assert key cell values in output).
- `--raw` prints JSON items.
- Empty items → "no data" message.
- API error (403) → Abort path (non-zero exit).

## Changelog

`changes/cli/+report-command.added.md`.
