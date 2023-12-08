import shlex
from unittest import mock

import httpx
import pytest

from jobbergate_cli.schemas import ApplicationResponse
from jobbergate_cli.subapps.applications.app import (
    HIDDEN_FIELDS,
    create,
    delete,
    download_files,
    get_one,
    list_all,
    pathlib,
    style_mapper,
    update,
)
from jobbergate_cli.text_tools import unwrap


def test_list_all__renders_paginated_results(
    make_test_app,
    dummy_context,
    cli_runner,
    mocker,
):
    test_app = make_test_app("list-all", list_all)
    mocked_pagination = mocker.patch("jobbergate_cli.subapps.applications.app.handle_pagination")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_pagination.assert_called_once_with(
        jg_ctx=dummy_context,
        url_path="/jobbergate/job-script-templates",
        abort_message="Couldn't retrieve applications list from API",
        params={"include_null_identifier": False, "user_only": False, "sort_ascending": False, "sort_field": "id"},
        title="Applications List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


@pytest.mark.parametrize("id_flag,separator", [("--id", "="), ("-i", " ")])
def test_get_one__success__using_id(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
    id_flag,
    separator,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_application_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split(f"get-one {id_flag}{separator}1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**dummy_application_data[0]),
        title="Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__success__using_identifier(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/dummy").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_application_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split("get-one --identifier=dummy"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**dummy_application_data[0]),
        title="Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__fails_with_neither_id_or_identifier(make_test_app, cli_runner):
    test_app = make_test_app("get-one", get_one)
    result = cli_runner.invoke(test_app, shlex.split("get-one"))
    assert result.exit_code != 0
    assert "You must supply either" in result.stdout


def test_get_one__fails_with_both_id_and_identifier(make_test_app, cli_runner):
    test_app = make_test_app("get-one", get_one)
    result = cli_runner.invoke(test_app, shlex.split("get-one --id=1 --identifier=dummy"))
    assert result.exit_code != 0
    assert "You may not supply both" in result.stdout


@pytest.mark.parametrize(
    "name_flag,application_path_flag,separator", [("--name", "--application-path", "="), ("-n", "-a", " ")]
)
def test_create__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application_dir,
    dummy_domain,
    cli_runner,
    mocker,
    name_flag,
    application_path_flag,
    separator,
):
    response_data = dummy_application_data[0]
    response_data["application_uploaded"] = False

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-script-templates")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=response_data,
        ),
    )

    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")
    mocked_upload.return_value = True

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                create {name_flag}{separator}dummy-name --identifier=dummy-identifier
                       {application_path_flag}{separator}{dummy_application_dir}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert create_route.called
    assert mocked_upload.called

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": True},
        title="Created Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_create__warns_but_does_not_abort_if_upload_fails(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application_dir,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    application_id = response_data["id"]

    create_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-script-templates")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    upload_route.mock(
        return_value=httpx.Response(httpx.codes.BAD_REQUEST),
    )

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                create --name=dummy-name --identifier=dummy-identifier
                       --application-path={dummy_application_dir}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert create_route.called
    assert upload_route.called
    assert "application files could not be uploaded" in result.stdout

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": False},
        title="Created Application",
        hidden_fields=HIDDEN_FIELDS,
    )


@pytest.mark.parametrize(
    "id_flag,application_path_flag,separator", [("--id", "--application-path", "="), ("-i", "-a", " ")]
)
def test_update__success_by_id(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application_dir,
    dummy_domain,
    cli_runner,
    mocker,
    id_flag,
    application_path_flag,
    separator,
):
    response_data = dummy_application_data[0]
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")
    mocked_upload.return_value = True

    get_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    get_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update {id_flag}{separator}{application_id} --update-identifier=dummy-identifier
                       {application_path_flag}{separator}{dummy_application_dir}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert get_route.called
    assert mocked_upload.called

    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**response_data),
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__success_by_identifier(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application_dir,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    application_identifier = response_data["identifier"]

    update_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{application_identifier}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")
    mocked_upload.return_value = True

    get_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{application_identifier}")
    get_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update --identifier={application_identifier} --update-identifier=dummy-identifier
                       --application-path={dummy_application_dir}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert get_route.called
    assert mocked_upload.called

    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**response_data),
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__does_not_upload_if_application_path_is_not_supplied(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    get_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    get_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update --id={application_id} --update-identifier=dummy-identifier
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert mocked_upload.not_called

    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**response_data),
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__warns_but_does_not_abort_if_upload_fails(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application_dir,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )

    get_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{application_id}")
    get_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=response_data,
        ),
    )
    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")
    mocked_upload.return_value = False

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update --id={application_id} --update-identifier=dummy-identifier
                       --application-path={dummy_application_dir}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert mocked_upload.called
    assert "application files could not be uploaded" in result.stdout

    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**response_data),
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


@pytest.mark.parametrize("id_flag,separator", [("--id", "="), ("-i", " ")])
def test_delete__success_by_id(respx_mock, make_test_app, dummy_domain, cli_runner, id_flag, separator):
    delete_route = respx_mock.delete(f"{dummy_domain}/jobbergate/job-script-templates/1")
    delete_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete {id_flag}{separator}1"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "Application delete succeeded" in result.stdout


def test_delete__success_by_identifier(respx_mock, make_test_app, dummy_domain, cli_runner):
    delete_route = respx_mock.delete(f"{dummy_domain}/jobbergate/job-script-templates/dummy")
    delete_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split("delete --identifier=dummy"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "Application delete succeeded" in result.stdout


class TestDownloadApplicationFiles:
    """
    Test the download application files subcommand.
    """

    @pytest.fixture()
    def test_app(self, make_test_app):
        """
        Fixture to create a test app.
        """
        return make_test_app("download", download_files)

    def test_download__success__using_id(
        self,
        respx_mock,
        test_app,
        dummy_application_data,
        dummy_domain,
        dummy_context,
        cli_runner,
        mocker,
        tmp_path,
    ):
        """
        Test that the download application files subcommand works as expected.
        """
        respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/1").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dummy_application_data[0],
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.terminal_message")

        list_of_files = [f"file-{i}" for i in range(3)]

        mocked_save_files = mocker.patch(
            "jobbergate_cli.subapps.applications.app.save_application_files", return_value=list_of_files
        )

        with mock.patch.object(pathlib.Path, "cwd", return_value=tmp_path):
            result = cli_runner.invoke(test_app, shlex.split("download --id=1"))

        assert mocked_save_files.called_with(
            dummy_context,
            ApplicationResponse(**dummy_application_data[0]),
            tmp_path,
        )

        assert result.exit_code == 0, f"download failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            f"A total of {len(list_of_files)} application files were successfully downloaded.",
            subject="Application download succeeded",
        )

    def test_download__success__using_identifier(
        self,
        respx_mock,
        test_app,
        dummy_application_data,
        dummy_domain,
        dummy_context,
        cli_runner,
        mocker,
        tmp_path,
    ):
        """
        Test that the download application files subcommand works as expected.
        """
        application_data = dummy_application_data[0]
        identifier = application_data["identifier"]

        respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{identifier}").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=dummy_application_data[0],
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.terminal_message")

        list_of_files = [f"file-{i}" for i in range(3)]

        mocked_save_files = mocker.patch(
            "jobbergate_cli.subapps.applications.app.save_application_files", return_value=list_of_files
        )

        with mock.patch.object(pathlib.Path, "cwd", return_value=tmp_path):
            result = cli_runner.invoke(test_app, shlex.split(f"download --identifier={identifier}"))

        assert mocked_save_files.called_with(
            dummy_context,
            ApplicationResponse(**dummy_application_data[0]),
            tmp_path,
        )

        assert result.exit_code == 0, f"download failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            f"A total of {len(list_of_files)} application files were successfully downloaded.",
            subject="Application download succeeded",
        )

    def test_download__fails_with_neither_id_or_identifier(self, test_app, cli_runner):
        """
        Test that the download application files subcommand fails when neither id nor identifier are supplied.
        """
        result = cli_runner.invoke(test_app, shlex.split("download"))
        assert result.exit_code != 0
        assert "You must supply either" in result.stdout

    def test_download__fails_with_both_id_and_identifier(self, test_app, cli_runner):
        """
        Test that the download application files subcommand fails when both id and identifier are supplied.
        """
        result = cli_runner.invoke(test_app, shlex.split("download --id=1 --identifier=dummy"))
        assert result.exit_code != 0
        assert "You may not supply both" in result.stdout
