import shlex

from jobbergate_cli.main import main


def test_main_command_with_ignore_username_and_password(
    make_test_app,
    cli_runner,
):
    test_app = make_test_app("jobbergate", main)

    result = cli_runner.invoke(test_app, shlex.split("jobbergate --username user --password pass"))
    assert result.exit_code == 0
    assert "No command provided" in result.stdout

    result = cli_runner.invoke(test_app, shlex.split("jobbergate -u user -p pass"))
    assert result.exit_code == 0
    assert "No command provided" in result.stdout
