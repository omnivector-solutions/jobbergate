import importlib
import json
import shlex
from unittest import mock

import httpx
import snick

from jobbergate_cli.subapps.job_scripts.app import (
    list_all,
    get_one,
    create,
    style_mapper,
    HIDDEN_FIELDS,
)
from jobbergate_cli.schemas import Pagination, ListResponseEnvelope


def test_list_all__makes_request_and_renders_results(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_job_script_data,
    dummy_domain,
    cli_runner,
):
    respx_mock.get(f"{dummy_domain}/job-scripts?all=false").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                results=dummy_job_script_data,
                pagination=dict(
                    total=3,
                )
            )
        ),
    )
    test_app = make_test_app("list-all", list_all)
    with mock.patch("jobbergate_cli.subapps.job_scripts.app.render_list_results") as mocked_render:
        result = cli_runner.invoke(test_app, ["list-all"])
        assert result.exit_code == 0, f"list-all failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            dummy_context,
            ListResponseEnvelope(
                results=dummy_job_script_data,
                pagination=Pagination(total=3),
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
):
    respx_mock.get(f"{dummy_domain}/job-scripts/1").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dummy_job_script_data[0],
        ),
    )
    test_app = make_test_app("get-one", get_one)
    with mock.patch("jobbergate_cli.subapps.job_scripts.app.render_single_result") as mocked_render:
        result = cli_runner.invoke(test_app, shlex.split("get-one --id=1"))
        assert result.exit_code == 0, f"get-one failed: {result.stdout}"
        mocked_render.assert_called_once_with(
            dummy_context,
            dummy_job_script_data[0],
            title="Job Script",
            hidden_fields=HIDDEN_FIELDS,
        )


def test_create__success(
    respx_mock,
    make_test_app,
    dummy_context,
    dummy_application_data,
    dummy_job_script_data,
    dummy_job_submission_data,
    dummy_domain,
    dummy_render_class,
    cli_runner,
    tmp_path,
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
    param_file_path.write_text(json.dumps(dict(
        qux="qux",
        quux="quux",
    )))

    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
        qux="QUX",
        quux="QUUX",
    )

    test_app = make_test_app("create", create)
    with mock.patch("jobbergate_cli.subapps.applications.app.render_single_result") as mocked_render:
        with mock.patch(
            "jobbergate_cli.subapps.job_scripts.app.fetch_application_data",
            return_value=application_data,
        ) as mocked_fetch_application_data:
            with mock.patch(
                "jobbergate_cli.subapps.job_submissions.tools.create_job_submission",
                return_value=job_submission_data,
            ) as mocked_create_job_submission:
                with mock.patch.object(
                    importlib.import_module("inquirer.prompt"),
                    "ConsoleRender",
                    new=dummy_render_class,
                ):
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
                        input="\n",  # To confirm that the job should be submitted right away
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
                    assert json.loads(create_route.calls.last.request.content) == dict(
                        foo="FOO",
                        bar="BAR",
                        baz="BAZ",
                        qux="qux",
                        quux="quux",
                        sbatch_params_1="1",
                        sbatch_params_2="2",
                        sbatch_params_3="3",
                    )

                    mocked_render.assert_any_call(
                        dummy_context,
                        job_script_data,
                        title="Created Job Script",
                        hidden_fields=HIDDEN_FIELDS,
                    )
