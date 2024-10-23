import shlex
from unittest import mock

import httpx
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ApplicationResponse
from jobbergate_cli.subapps.applications.app import (
    HIDDEN_FIELDS,
    clone,
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
        nested_response_model_cls=ApplicationResponse,
    )


@pytest.mark.parametrize(
    "selector_template",
    [
        "{id}",
        "-i {id}",
        "--id={id}",
        "--id {id}",
        "{identifier}",
        "--identifier={identifier}",
        "--identifier {identifier}",
    ],
)
def test_get_one__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
    selector_template,
):
    application_data = dummy_application_data[0]
    id = application_data["id"]
    identifier = application_data["identifier"]

    url_selector = identifier if "identifier" in selector_template else id
    cli_selector = selector_template.format(id=id, identifier=identifier)

    respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{url_selector}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_application_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split(f"get-one {cli_selector}"))
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
    assert "You must supply one and only one selection value" in result.stdout


@pytest.mark.parametrize(
    "cli_selector",
    ["1 --id 2", "foo --identifier bar", "--id 1 --identifier dummy"],
)
def test_get_one__fails_with_both_id_and_identifier(make_test_app, cli_runner, cli_selector):
    test_app = make_test_app("get-one", get_one)
    result = cli_runner.invoke(test_app, shlex.split(f"get-one {cli_selector}"))
    assert result.exit_code != 0
    assert "You must supply one and only one selection value" in result.stdout


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
    assert result.exit_code == 1, f"create failed: {result.stdout}"
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
    "selector_template",
    [
        "{id}",
        "-i {id}",
        "--id={id}",
        "--id {id}",
        "{identifier}",
        "--identifier={identifier}",
        "--identifier {identifier}",
    ],
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
    selector_template,
):
    application_data = dummy_application_data[0]
    id = application_data["id"]
    identifier = application_data["identifier"]

    url_selector = identifier if "identifier" in selector_template else id
    cli_selector = selector_template.format(id=id, identifier=identifier)

    update_route = respx_mock.put(f"{dummy_domain}/jobbergate/job-script-templates/{url_selector}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=application_data,
        ),
    )

    mocked_upload = mocker.patch("jobbergate_cli.subapps.applications.app.upload_application")
    mocked_upload.return_value = True

    get_route = respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{url_selector}")
    get_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=application_data,
        ),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            unwrap(
                f"""
                update {cli_selector} --update-identifier=dummy-identifier
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
        ApplicationResponse(**application_data),
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
    assert mocked_upload.call_count == 0

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
    mocked_upload = mocker.patch(
        "jobbergate_cli.subapps.applications.app.upload_application",
        side_effect=Abort("Failed to upload application files"),
    )

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
    assert result.exit_code == 1, f"update failed: {result.stdout}"
    assert update_route.called
    assert mocked_upload.called
    assert "application files could not be uploaded" in result.stdout

    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**response_data),
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


@pytest.mark.parametrize(
    "selector_template",
    [
        "{id}",
        "-i {id}",
        "--id={id}",
        "--id {id}",
        "{identifier}",
        "--identifier={identifier}",
        "--identifier {identifier}",
    ],
)
def test_delete__success(respx_mock, make_test_app, dummy_domain, cli_runner, selector_template):
    id = 1
    identifier = "some-identifier"

    url_selector = identifier if "identifier" in selector_template else id
    cli_selector = selector_template.format(id=id, identifier=identifier)

    delete_route = respx_mock.delete(f"{dummy_domain}/jobbergate/job-script-templates/{url_selector}")
    delete_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete {cli_selector}"))
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

    @pytest.mark.parametrize(
        "selector_template",
        [
            "{id}",
            "-i {id}",
            "--id={id}",
            "--id {id}",
            "{identifier}",
            "--identifier={identifier}",
            "--identifier {identifier}",
        ],
    )
    def test_download__success(
        self,
        respx_mock,
        test_app,
        dummy_application_data,
        dummy_domain,
        dummy_context,
        cli_runner,
        mocker,
        tmp_path,
        selector_template,
    ):
        """
        Test that the download application files subcommand works as expected.
        """
        application_data = dummy_application_data[0]
        id = application_data["id"]
        identifier = application_data["identifier"]

        url_selector = identifier if "identifier" in selector_template else id
        cli_selector = selector_template.format(id=id, identifier=identifier)

        respx_mock.get(f"{dummy_domain}/jobbergate/job-script-templates/{url_selector}").mock(
            return_value=httpx.Response(
                httpx.codes.OK,
                json=application_data,
            ),
        )
        mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.terminal_message")

        list_of_files = [f"file-{i}" for i in range(3)]

        mocked_save_files = mocker.patch(
            "jobbergate_cli.subapps.applications.app.save_application_files", return_value=list_of_files
        )

        with mock.patch.object(pathlib.Path, "cwd", return_value=tmp_path):
            result = cli_runner.invoke(test_app, shlex.split(f"download {cli_selector}"))

        mocked_save_files.assert_called_with(
            dummy_context,
            application_data=ApplicationResponse(**application_data),
            destination_path=tmp_path,
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
        assert "You must supply one and only one selection value" in result.stdout

    def test_download__fails_with_both_id_and_identifier(self, test_app, cli_runner):
        """
        Test that the download application files subcommand fails when both id and identifier are supplied.
        """
        result = cli_runner.invoke(test_app, shlex.split("download --id=1 --identifier=dummy"))
        assert result.exit_code != 0
        assert "You must supply one and only one selection value" in result.stdout


@pytest.mark.parametrize(
    "selector_template",
    [
        "{id}",
        "-i {id}",
        "--id={id}",
        "--id {id}",
        "{identifier}",
        "--identifier={identifier}",
        "--identifier {identifier}",
    ],
)
def test_clone__success(
    respx_mock,
    make_test_app,
    dummy_application_data,
    dummy_domain,
    dummy_context,
    cli_runner,
    mocker,
    selector_template,
):
    """
    Test that the clone application subcommand works as expected.
    """

    application_data = dummy_application_data[0]
    id = application_data["id"]
    identifier = application_data["identifier"]

    url_selector = identifier if "identifier" in selector_template else id
    cli_selector = selector_template.format(id=id, identifier=identifier)

    clone_route = respx_mock.post(f"{dummy_domain}/jobbergate/job-script-templates/clone/{url_selector}").mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=application_data,
        ),
    )
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")

    test_app = make_test_app("clone", clone)
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            "clone {} --application-identifier={} --application-name={} --application-desc={}".format(
                cli_selector,
                shlex.quote(application_data["identifier"]),
                shlex.quote(application_data["name"]),
                shlex.quote(application_data["description"]),
            ),
        ),
    )

    assert clone_route.called

    assert result.exit_code == 0, f"clone failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ApplicationResponse(**application_data),
        title="Cloned Application",
        hidden_fields=HIDDEN_FIELDS,
    )
