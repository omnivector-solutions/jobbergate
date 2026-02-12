import shlex

from jobbergate_cli.main import main, login, logout


def test_main_command_with_ignore_username_and_password(make_test_app, cli_runner):
    test_app = make_test_app("jobbergate", main)

    result = cli_runner.invoke(test_app, shlex.split("jobbergate --username user --password pass"))
    assert result.exit_code == 0

    result = cli_runner.invoke(test_app, shlex.split("jobbergate -u user -p pass"))
    assert result.exit_code == 0


def test_login_success(make_test_app, cli_runner, dummy_context, attach_persona, mocker):
    test_app = make_test_app("login", login)

    mocked_login = mocker.patch.object(dummy_context.authentication_handler, "login")

    attach_persona("dummy@dummy.com")

    result = cli_runner.invoke(test_app, shlex.split("login"))
    assert result.exit_code == 0

    assert mocked_login.call_count == 1
    assert "User was logged in with email 'dummy@dummy.com'" in result.stdout


def test_logout_success(make_test_app, cli_runner, dummy_context, mocker):
    test_app = make_test_app("logout", logout)

    mocked_logout = mocker.patch.object(dummy_context.authentication_handler, "logout")

    result = cli_runner.invoke(test_app, shlex.split("logout"))
    assert result.exit_code == 0

    assert mocked_logout.call_count == 1
    assert "User was logged out" in result.stdout
