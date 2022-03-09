import typer

from jobbergate_cli.compat import add_legacy_compatible_commands

def test_list_all__makes_request_and_renders_results():
    test_app = typer.Typer()
    add_legacy_compatible_commands(test_app)

    registered_command_names = [c.name for c in test_app.registered_commands]
    assert sorted(registered_command_names) == sorted([
        "list-applications",
        "get-application",
        "create-application",
        "delete-application",
        "update-application",
        "list-job-scripts",
        "get-job-script",
        "create-job-script",
        "update-job-script",
        "delete-job-script",
        "list-job-submissions",
        "get-job-submission",
        "create-job-submission",
        "delete-job-submission",
    ])
