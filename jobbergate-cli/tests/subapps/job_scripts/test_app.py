import importlib
import json
import shlex

import httpx
import snick
import yaml

from jobbergate_cli.schemas import ListResponseEnvelope, Pagination
from jobbergate_cli.subapps.job_scripts.app import (
    HIDDEN_FIELDS,
    JOB_SUBMISSION_HIDDEN_FIELDS,
    create,
    delete,
    get_one,
    list_all,
    style_mapper,
    update,
)


def test_list_all__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/job-scripts?all=false").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_script_data,
                pagination=dict(
                    total=3,
                ),
            ),
        ),
    )
    test_app = make_test_app("list-all", list_all)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results")
    result = cli_runner.invoke(test_app, ["list-all"])
    assert result.exit_code == 0, f"list-all failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        ListResponseEnvelope(
            results=dummy_job_script_data,
            pagination=Pagination(total=3, start=None, limit=None),
        ),
        title="Job Scripts List",
        style_mapper=style_mapper,
        hidden_fields=HIDDEN_FIELDS,
    )


def test_get_one__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    respx_mock.get(f"{dummy_domain}/job-scripts/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_script_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    result = cli_runner.invoke(test_app, shlex.split("get-one --id=1"))
    assert result.exit_code == 0, f"get-one failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        dummy_job_script_data[0],
        title="Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_create__full_run_including_non_fast_mode_and_job_submission(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_job_script_data,
    dummy_job_submission_data,
    dummy_domain,
    dummy_render_class,
    dummy_config_source,
    cli_runner,
    tmp_path,
    attach_persona,
    mocker,
):

    application_data = dummy_application_data[0]
    application_id = application_data["id"]

    job_script_data = dummy_job_script_data[0]
    job_script_id = job_script_data["id"]

    job_submission_data = dummy_job_submission_data[0]

    create_route = respx_mock.post(f"{dummy_domain}/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_script_data,
        ),
    )

    sbatch_params = " ".join(f"--sbatch-params={i}" for i in (1, 2, 3))

    param_file_path = tmp_path / "param_file.json"
    param_file_path.write_text(
        json.dumps(
            dict(
                qux="qux",
                quux="quux",
            )
        )
    )

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
        qux="QUX",
        quux="QUUX",
    )

    attach_persona("dummy@dummy.com")

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.app.fetch_application_data",
        return_value=application_data,
    )
    mocked_create_job_submission = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.app.create_job_submission",
        return_value=job_submission_data,
    )
    mocker.patch.object(
        importlib.import_module("inquirer.prompt"),
        "ConsoleRender",
        new=dummy_render_class,
    )
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                create --name=dummy-name
                       --application-id={application_id}
                       --param-file={param_file_path}
                       {sbatch_params}
                """
            )
        ),
        input="y\n",  # To confirm that the job should be submitted right away
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert mocked_fetch_application_data.called_once_with(
        dummy_context,
        id=application_id,
        identifier=None,
    )
    assert mocked_create_job_submission.called_once_with(
        dummy_context,
        job_script_id,
        "dummy-name",
    )
    assert create_route.called
    content = json.loads(create_route.calls.last.request.content)
    unpacked_content = {
        **content,
        "param_dict": json.loads(content["param_dict"]),
    }
    assert unpacked_content == dict(
        param_dict=dict(
            **yaml.safe_load(dummy_config_source),
            job_script_name="dummy-name",
            application_id=application_id,
            foo="FOO",
            bar="BAR",
            baz="BAZ",
            qux="qux",
            quux="quux",
        ),
        job_script_name="dummy-name",
        sbatch_params_0="1",
        sbatch_params_1="2",
        sbatch_params_2="3",
        sbatch_params_len=3,
    )

    mocked_render.assert_has_calls(
        [
            mocker.call(
                dummy_context,
                job_script_data,
                title="Created Job Script",
                hidden_fields=HIDDEN_FIELDS,
            ),
            mocker.call(
                dummy_context,
                job_submission_data,
                title="Created Job Submission (Fast Mode)",
                hidden_fields=JOB_SUBMISSION_HIDDEN_FIELDS,
            ),
        ]
    )


def test_create__with_fast_mode_and_no_job_submission(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_job_script_data,
    dummy_domain,
    dummy_config_source,
    cli_runner,
    tmp_path,
    attach_persona,
    mocker,
):

    application_data = dummy_application_data[0]
    application_id = application_data["id"]

    job_script_data = dummy_job_script_data[0]

    create_route = respx_mock.post(f"{dummy_domain}/job-scripts")
    create_route.mock(
        return_value=httpx.Response(
            httpx.codes.CREATED,
            json=job_script_data,
        ),
    )

    sbatch_params = " ".join(f"--sbatch-params={i}" for i in (1, 2, 3))

    param_file_path = tmp_path / "param_file.json"
    param_file_path.write_text(
        json.dumps(
            dict(
                foo="foo",
                bar="bar",
                baz="baz",
                qux="qux",
                quux="quux",
            )
        )
    )

    attach_persona("dummy@dummy.com")

    test_app = make_test_app("create", create)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    mocked_fetch_application_data = mocker.patch(
        "jobbergate_cli.subapps.job_scripts.app.fetch_application_data",
        return_value=application_data,
    )
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                create --name=dummy-name
                       --application-id={application_id}
                       --param-file={param_file_path}
                       --fast
                       --no-submit
                       {sbatch_params}
                """
            )
        ),
    )
    assert result.exit_code == 0, f"create failed: {result.stdout}"
    assert mocked_fetch_application_data.called_once_with(
        dummy_context,
        id=application_id,
        identifier=None,
    )
    assert create_route.called
    content = json.loads(create_route.calls.last.request.content)
    unpacked_content = {
        **content,
        "param_dict": json.loads(content["param_dict"]),
    }
    assert unpacked_content == dict(
        param_dict=dict(
            **yaml.safe_load(dummy_config_source),
            job_script_name="dummy-name",
            application_id=application_id,
            foo="foo",
            bar="bar",
            baz="baz",
            qux="qux",
            quux="quux",
        ),
        job_script_name="dummy-name",
        sbatch_params_0="1",
        sbatch_params_1="2",
        sbatch_params_2="3",
        sbatch_params_len=3,
    )

    mocked_render.assert_called_once_with(
        dummy_context,
        job_script_data,
        title="Created Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_update__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
    mocker,
):
    job_script_data = dummy_job_script_data[0]
    job_script_id = job_script_data["id"]

    new_job_script_data_as_string = json.dumps({"application.sh": "#!bin/bash \\n echo so dumb"})
    new_job_script_data = {
        **job_script_data,
        "job_script_data_as_string": new_job_script_data_as_string,
    }
    respx_mock.put(f"{dummy_domain}/job-scripts/{job_script_id}").mock(
        return_value=httpx.Response(httpx.codes.ACCEPTED, json=new_job_script_data),
    )
    test_app = make_test_app("update", update)
    mocked_render = mocker.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result")
    result = cli_runner.invoke(
        test_app,
        shlex.split(
            snick.unwrap(
                f"""
                update --id={job_script_id}
                       --job-script='{new_job_script_data_as_string}'
                """
            )
        ),
    )
    assert result.exit_code == 0, f"update failed: {result.stdout}"
    mocked_render.assert_called_once_with(
        dummy_context,
        new_job_script_data,
        title="Updated Job Script",
        hidden_fields=HIDDEN_FIELDS,
    )


def test_delete__makes_request_and_sends_terminal_message(
    respx_mock,
    make_test_app,
    dummy_domain,
    cli_runner,
):
    job_script_id = 13

    delete_route = respx_mock.delete(f"{dummy_domain}/job-scripts/{job_script_id}").mock(
        return_value=httpx.Response(httpx.codes.NO_CONTENT),
    )
    test_app = make_test_app("delete", delete)
    result = cli_runner.invoke(test_app, shlex.split(f"delete --id={job_script_id}"))
    assert result.exit_code == 0, f"delete failed: {result.stdout}"
    assert delete_route.called
    assert "JOB SCRIPT DELETE SUCCEEDED"
