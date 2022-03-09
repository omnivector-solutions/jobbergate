import shlex

import httpx
import snick

from jobbergate_cli.subapps.applications.app import (
    list_all,
    get_one,
    create,
    update,
    delete,
    style_mapper,
    HIDDEN_FIELDS,
)
from jobbergate_cli.schemas import Pagination, ListResponseEnvelope


def test_list_all__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/applications").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_application_data,
                pagination=dict(
                    total=3,
                )
            )
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_list_results")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_application_data,
            pagination=Pagination(total=3),
        ),
        title="Applications List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__success__using_id(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/applications/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_application_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split("get-one --id=1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        dummy_application_data[0],
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
    respx_mock.get(f"{dummy_domain}/applications?identifier=dummy").mock(
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
        dummy_application_data[0],
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


def test_create__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    response_data["application_uploaded"] = False
    application_id = response_data["id"]

    create_route = respx_mock.post(f"{dummy_domain}/applications")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.post(f"{dummy_domain}/applications/{application_id}/upload")
    upload_route.mock(return_value=httpx.Response(httpx.codes.CREATED))

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                create --name=dummy-name --identifier=dummy-identifier
                       --application-path={dummy_application}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert create_route.called
    assert upload_route.called

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
    dummy_application,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    response_data["application_uploaded"] = False
    application_id = response_data["id"]

    create_route = respx_mock.post(f"{dummy_domain}/applications")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.post(f"{dummy_domain}/applications/{application_id}/upload")
    upload_route.mock(
        return_value=httpx.Response(httpx.codes.BAD_REQUEST),
    )

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                create --name=dummy-name --identifier=dummy-identifier
                       --application-path={dummy_application}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert create_route.called
    assert upload_route.called
    assert "zipped application files could not be uploaded" in result.stdout

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": False},
        title="Created Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    response_data["application_uploaded"] = False
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/applications/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.ACCEPTED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.post(f"{dummy_domain}/applications/{application_id}/upload")
    upload_route.mock(
        return_value=httpx.Response(httpx.codes.CREATED),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                update --id={application_id} --identifier=dummy-identifier
                       --application-path={dummy_application}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert upload_route.called

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": True},
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
    response_data["application_uploaded"] = False
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/applications/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.ACCEPTED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.post(f"{dummy_domain}/applications/{application_id}/upload")
    upload_route.mock(
        return_value=httpx.Response(httpx.codes.CREATED),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                update --id={application_id} --identifier=dummy-identifier
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert not upload_route.called

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": False},
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__warns_but_does_not_abort_if_upload_fails(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_application,
    dummy_domain,
    cli_runner,
    mocker,
):
    response_data = dummy_application_data[0]
    response_data["application_uploaded"] = False
    application_id = response_data["id"]

    update_route = respx_mock.put(f"{dummy_domain}/applications/{application_id}")
    update_route.mock(
        return_value=httpx.Response(
            httpx.codes.ACCEPTED,
            json=response_data,
        ),
    )

    upload_route = respx_mock.post(f"{dummy_domain}/applications/{application_id}/upload")
    upload_route.mock(
        return_value=httpx.Response(httpx.codes.BAD_REQUEST),
    )

    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.applications.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                update --id={application_id} --identifier=dummy-identifier
                       --application-path={dummy_application}
                       --application-desc="This application is kinda dumb, actually"
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    assert update_route.called
    assert upload_route.called
    assert "zipped application files could not be uploaded" in result.stdout

    mocked_render.assert_called_once_with(
        dummy_context,
        {**response_data, "application_uploaded": False},
        title="Updated Application",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_delete__success(respx_mock, make_test_app, dummy_domain, cli_runner):
    delete_route = respx_mock.delete(f"{dummy_domain}/applications/1")
    delete_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    delete_upload_route = respx_mock.delete(f"{dummy_domain}/applications/1/upload")
    delete_upload_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(
        test_app,
        shlex.split("delete --id=1")
    )
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert delete_upload_route.called
    assert "APPLICATION DELETE SUCCEEDED" in result.stdout


def test_delete__warns_but_does_not_abort_if_delete_upload_fails(respx_mock, make_test_app, dummy_domain, cli_runner):
    delete_route = respx_mock.delete(f"{dummy_domain}/applications/1")
    delete_route.mock(return_value=httpx.Response(httpx.codes.NO_CONTENT))

    delete_upload_route = respx_mock.delete(f"{dummy_domain}/applications/1/upload")
    delete_upload_route.mock(return_value=httpx.Response(httpx.codes.BAD_REQUEST))

    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(
        test_app,
        shlex.split("delete --id=1")
    )
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert delete_upload_route.called
    assert "FILE DELETE FAILED" in result.stdout
