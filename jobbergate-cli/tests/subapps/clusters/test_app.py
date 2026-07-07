from jobbergate_cli.context import active_context
from jobbergate_cli.subapps.clusters.app import list_all


def test_list_all__makes_request_and_renders_results(
    make_test_app,
    attach_persona,
    seed_clusters,
    cli_runner,
    mocker,
):
    attach_persona("dummy@dummy.com", client_id="dummy-cluster")
    seed_clusters("dummy-cluster")
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.clusters.app.terminal_message")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        "dummy-cluster",
        subject="Cluster Names",
        color="yellow",
        indent=True,
    )


def test_list_all__direct_invocation_uses_the_active_context(
    attach_persona,
    seed_clusters,
    dummy_context,
    mocker,
):
    """Direct invocation with no ctx argument resolves the Jobbergate context from the active context."""
    attach_persona("dummy@dummy.com", client_id="dummy-cluster")
    seed_clusters("dummy-cluster")
    mocked_render = mocker.patch("jobbergate_cli.subapps.clusters.app.terminal_message")

    with active_context(dummy_context):
        list_all()

    mocked_render.assert_called_once_with(
        "dummy-cluster",
        subject="Cluster Names",
        color="yellow",
        indent=True,
    )
