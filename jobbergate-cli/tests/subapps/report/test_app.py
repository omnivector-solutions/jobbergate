import httpx

from jobbergate_cli.subapps.report.app import status, submissions, templates

STATUS_PAYLOAD = {
    "items": [
        {
            "client_id": "cluster-a",
            "created_at": "2026-09-01T00:00:00Z",
            "updated_at": "2026-10-27T12:00:00Z",
            "last_reported": "2026-10-27T12:00:00Z",
            "interval": 60,
            "is_healthy": True,
        },
        {
            "client_id": "cluster-b",
            "created_at": "2026-09-01T00:00:00Z",
            "updated_at": "2026-10-20T12:00:00Z",
            "last_reported": "2026-10-20T12:00:00Z",
            "interval": 60,
            "is_healthy": False,
        },
    ],
    "total": 2,
    "page": 1,
    "size": 50,
    "pages": 1,
}

TEMPLATES_PAYLOAD = {
    "start_time": "2026-09-08T00:00:00Z",
    "end_time": "2026-09-10T00:00:00Z",
    "interval": "day",
    "items": [
        {
            "bucket": "2026-09-08T00:00:00Z",
            "client_id": "cluster-a",
            "template_id": 3,
            "template_identifier": "template-a",
            "count": 2,
        },
        {
            "bucket": "2026-09-09T00:00:00Z",
            "client_id": "cluster-b",
            "template_id": 7,
            "template_identifier": "template_id:7",
            "count": 1,
        },
    ],
}

SUBMISSIONS_PAYLOAD = {
    "start_time": "2026-09-08T00:00:00Z",
    "end_time": "2026-09-10T00:00:00Z",
    "interval": "day",
    "items": [
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
    ],
}


def test_templates__forwards_options_and_renders_table(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    route = respx_mock.get(f"{dummy_domain}/jobbergate/analytics/templates").mock(
        return_value=httpx.Response(httpx.codes.OK, json=TEMPLATES_PAYLOAD),
    )
    test_app = make_test_app("templates", templates)

    result = cli_runner.invoke(
        test_app,
        [
            "templates",
            "--start-time",
            "2026-09-08T00:00:00",
            "--end-time",
            "2026-09-10T00:00:00",
            "--interval",
            "day",
        ],
    )

    assert result.exit_code == 0, f"templates failed: {result.stdout}"
    assert route.called
    params = route.calls.last.request.url.params
    assert params["start_time"] == "2026-09-08T00:00:00"
    assert params["end_time"] == "2026-09-10T00:00:00"
    assert params["interval"] == "day"
    assert "template-a" in result.stdout
    assert "cluster-a" in result.stdout


def test_templates__omits_unset_options(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    route = respx_mock.get(f"{dummy_domain}/jobbergate/analytics/templates").mock(
        return_value=httpx.Response(httpx.codes.OK, json=TEMPLATES_PAYLOAD),
    )
    test_app = make_test_app("templates", templates)

    result = cli_runner.invoke(test_app, ["templates"])

    assert result.exit_code == 0, f"templates failed: {result.stdout}"
    assert str(route.calls.last.request.url).endswith("/jobbergate/analytics/templates")


def test_templates__raw_output_prints_json_items(
    make_test_app,
    cli_runner,
    dummy_domain,
    dummy_context,
    respx_mock,
    mocker,
):
    dummy_context.raw_output = True
    respx_mock.get(f"{dummy_domain}/jobbergate/analytics/templates").mock(
        return_value=httpx.Response(httpx.codes.OK, json=TEMPLATES_PAYLOAD),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.report.app.render_json")
    test_app = make_test_app("templates", templates)

    result = cli_runner.invoke(test_app, ["templates"])

    assert result.exit_code == 0, f"templates failed: {result.stdout}"
    mocked_render.assert_called_once_with(TEMPLATES_PAYLOAD["items"])


def test_templates__empty_report_shows_no_data_message(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
    mocker,
):
    payload = dict(TEMPLATES_PAYLOAD, items=[])
    respx_mock.get(f"{dummy_domain}/jobbergate/analytics/templates").mock(
        return_value=httpx.Response(httpx.codes.OK, json=payload),
    )
    mocked_message = mocker.patch("jobbergate_cli.subapps.report.app.terminal_message")
    test_app = make_test_app("templates", templates)

    result = cli_runner.invoke(test_app, ["templates"])

    assert result.exit_code == 0, f"templates failed: {result.stdout}"
    mocked_message.assert_called_once_with("No data in the selected window", subject="Template usage")


def test_templates__aborts_on_api_error(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/analytics/templates").mock(
        return_value=httpx.Response(
            httpx.codes.FORBIDDEN,
            json=dict(detail="Not enough permissions"),
        ),
    )
    test_app = make_test_app("templates", templates)

    result = cli_runner.invoke(test_app, ["templates"])

    assert result.exit_code != 0


def test_status__renders_cluster_statuses(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    route = respx_mock.get(f"{dummy_domain}/jobbergate/clusters/status").mock(
        return_value=httpx.Response(httpx.codes.OK, json=STATUS_PAYLOAD),
    )
    test_app = make_test_app("status", status)

    result = cli_runner.invoke(test_app, ["status", "--page", "1"])

    assert result.exit_code == 0, f"status failed: {result.stdout}"
    assert route.called
    assert "cluster-a" in result.stdout
    assert "cluster-b" in result.stdout
    assert "True" in result.stdout
    assert "False" in result.stdout


def test_status__hides_audit_timestamps(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/clusters/status").mock(
        return_value=httpx.Response(httpx.codes.OK, json=STATUS_PAYLOAD),
    )
    test_app = make_test_app("status", status)

    result = cli_runner.invoke(test_app, ["status", "--page", "1"])

    assert result.exit_code == 0, f"status failed: {result.stdout}"
    assert "created_at" not in result.stdout
    assert "updated_at" not in result.stdout


def test_submissions__forwards_options_and_renders_table(
    make_test_app,
    cli_runner,
    dummy_domain,
    respx_mock,
):
    route = respx_mock.get(f"{dummy_domain}/jobbergate/analytics/submissions").mock(
        return_value=httpx.Response(httpx.codes.OK, json=SUBMISSIONS_PAYLOAD),
    )
    test_app = make_test_app("submissions", submissions)

    result = cli_runner.invoke(test_app, ["submissions", "--interval", "week"])

    assert result.exit_code == 0, f"submissions failed: {result.stdout}"
    assert route.called
    assert route.calls.last.request.url.params["interval"] == "week"
    assert "SUBMITTED" in result.stdout
    assert "RUNNING" in result.stdout


def test_submissions__raw_output_prints_json_items(
    make_test_app,
    cli_runner,
    dummy_domain,
    dummy_context,
    respx_mock,
    mocker,
):
    dummy_context.raw_output = True
    respx_mock.get(f"{dummy_domain}/jobbergate/analytics/submissions").mock(
        return_value=httpx.Response(httpx.codes.OK, json=SUBMISSIONS_PAYLOAD),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.report.app.render_json")
    test_app = make_test_app("submissions", submissions)

    result = cli_runner.invoke(test_app, ["submissions"])

    assert result.exit_code == 0, f"submissions failed: {result.stdout}"
    mocked_render.assert_called_once_with(SUBMISSIONS_PAYLOAD["items"])
