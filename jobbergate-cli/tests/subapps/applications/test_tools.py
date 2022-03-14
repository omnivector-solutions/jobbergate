import importlib
import pathlib
import re
import tarfile

import httpx
import pytest
import snick
import yaml

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ApplicationResponse, JobbergateApplicationConfig
from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.tools import (
    build_application_tarball,
    dump_full_config,
    execute_application,
    fetch_application_data,
    load_application_data,
    load_application_from_source,
    load_default_config,
    read_application_module,
    validate_application_files,
)


def test_validate_application_files__success(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()
    application_module = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    application_module.write_text(
        snick.dedent(
            """
            import sys

            print(f"Got some args, yo: {sys.argv}")
            """
        )
    )
    application_config = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    application_config.write_text(
        snick.dedent(
            """
            foo:
              bar: baz
            """
        )
    )
    validate_application_files(application_path)


def test_validate_application_files__fails_if_application_directory_does_not_exist(tmp_path):
    application_path = tmp_path / "dummy"

    match_pattern = re.compile(
        f"application files in {application_path} were invalid.*directory {application_path} does not exist",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_files(application_path)


def test_validate_application_files__fails_if_application_module_does_not_exist(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()

    match_pattern = re.compile(
        f"application files in {application_path} were invalid.*does not contain required application module",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_files(application_path)


def test_validate_application_files__fails_if_application_module_is_not_valid_python(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()
    application_module = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    application_module.write_text("[")

    match_pattern = re.compile(
        f"application files in {application_path} were invalid.*not valid python",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_files(application_path)


def test_validate_application_files__fails_if_application_config_does_not_exist(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()

    match_pattern = re.compile(
        f"application files in {application_path} were invalid.*does not contain required configuration file",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_files(application_path)


def test_validate_application_files__fails_if_application_config_is_not_valid_yaml(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()
    application_config = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    application_config.write_text(":")

    match_pattern = re.compile(
        f"application files in {application_path} were invalid.*not valid YAML",
        flags=re.DOTALL,
    )

    with pytest.raises(Abort, match=match_pattern):
        validate_application_files(application_path)


def test_dump_full_config(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()
    template_root_path = application_path / "templates"
    template_root_path.mkdir()
    file1 = template_root_path / "file1"
    file1.write_text("foo")
    file2 = template_root_path / "file2"
    file2.write_text("bar")
    config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config_path.write_text(
        snick.dedent(
            """
            jobbergate_config:
              default_template: test-job-script.py.j2
              output_directory: .
            application_config:
              partition: debug
            """
        )
    )

    assert yaml.safe_load(dump_full_config(application_path)) == dict(
        jobbergate_config=dict(
            default_template="test-job-script.py.j2",
            output_directory=".",
            template_files=[
                "templates/file1",
                "templates/file2",
            ],
        ),
        application_config=dict(
            partition="debug",
        ),
    )


def test_load_default_config():
    default_config = load_default_config()
    assert default_config == JOBBERGATE_APPLICATION_CONFIG
    default_config["foo"] = "bar"
    assert default_config != JOBBERGATE_APPLICATION_CONFIG


def test_read_application_module(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()

    module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    module_path.write_text("print('foo')")

    assert read_application_module(application_path) == "print('foo')"


def test_build_application_tarball(
    tmp_path,
    dummy_application_dir,
    dummy_config_source,
    dummy_module_source,
    dummy_template_source,
):
    build_path = tmp_path / "build"
    build_path.mkdir()
    tar_path = build_application_tarball(dummy_application_dir, build_path)

    assert tar_path.exists()
    assert tarfile.is_tarfile(tar_path)

    extract_path = tmp_path / "extract"
    extract_path.mkdir()
    with tarfile.open(tar_path) as tar_file:
        tar_file.extractall(extract_path)

    module_path = extract_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    assert module_path.exists()
    assert module_path.read_text() == dummy_module_source

    config_path = extract_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    assert config_path.exists()
    assert config_path.read_text() == dummy_config_source

    template_root_path = extract_path / "templates"
    assert template_root_path.exists()

    template_path = template_root_path / "job-script-template.py.j2"
    assert template_path.exists()
    assert template_path.read_text() == dummy_template_source

    ignored_path = extract_path / "ignored"
    assert not ignored_path.exists()


def test_fetch_application_data__success__using_id(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    app_data = dummy_application_data[0]
    app_id = app_data["id"]
    fetch_route = respx_mock.get(f"{dummy_domain}/applications/{app_id}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, id=app_id)
    assert fetch_route.called
    assert result == ApplicationResponse(**app_data)


def test_fetch_application_data__success__using_identifier(
    respx_mock,
    dummy_context,
    dummy_application_data,
    dummy_domain,
):
    app_data = dummy_application_data[0]
    app_identifier = app_data["application_identifier"]
    fetch_route = respx_mock.get(f"{dummy_domain}/applications?identifier={app_identifier}")
    fetch_route.mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=app_data,
        ),
    )

    result = fetch_application_data(dummy_context, identifier=app_identifier)
    assert fetch_route.called
    assert result == ApplicationResponse(**app_data)


def test_fetch_application_data__fails_with_both_id_or_identifier(dummy_context):
    with pytest.raises(Abort, match="You may not supply both"):
        fetch_application_data(dummy_context, id=1, identifier="one")


def test_fetch_application_data__fails_with_neither_id_or_identifier(dummy_context):
    with pytest.raises(Abort, match="You must supply either"):
        fetch_application_data(dummy_context)


def test_load_application_data__success(dummy_module_source, dummy_config_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_file=dummy_module_source,
        application_config=dummy_config_source,
    )
    (app_config, app_module) = load_application_data(app_data)
    assert isinstance(app_module, JobbergateApplicationBase)
    assert isinstance(app_config, JobbergateApplicationConfig)


def test_load_application_data__fails_if_application_module_cannot_be_loaded_from_source(dummy_config_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_file="Not python at all",
        application_config=dummy_config_source,
    )

    with pytest.raises(Abort, match="The application source fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_data__fails_if_application_config_is_not_valid_YAML(dummy_module_source):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_file=dummy_module_source,
        application_config=":",
    )

    with pytest.raises(Abort, match="The application config fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_data__fails_if_application_config_is_not_valid_JobbergateApplicationConfig(
    dummy_module_source,
):
    app_data = ApplicationResponse(
        id=13,
        application_name="dummy",
        application_owner_email="dummy@dummy.org",
        application_uploaded=True,
        application_file=dummy_module_source,
        application_config=snick.dedent(
            """
            foo: bar
            """
        ),
    )

    with pytest.raises(Abort, match="The application config fetched from the API is not valid"):
        load_application_data(app_data)


def test_load_application_from_source__success(dummy_module_source, dummy_jobbergate_application_config):
    application = load_application_from_source(dummy_module_source, dummy_jobbergate_application_config)
    assert isinstance(application, JobbergateApplicationBase)
    assert application.mainflow
    assert application.jobbergate_config == dict(
        default_template="test-job-script.py.j2",
        template_files=[pathlib.Path("test-job-script.py.j2")],
        output_directory=pathlib.Path("."),
        supporting_files=None,
        supporting_files_output_name=None,
        job_script_name=None,
    )
    assert application.application_config == dict(
        foo="foo",
        bar="bar",
        baz="baz",
    )


def test_execute_application__basic(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
    )
    assert app_params == dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )


def test_execute_application__with_supplied_params(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
        supplied_params=dict(foo="oof"),
    )
    assert app_params == dict(
        foo="oof",
        bar="BAR",
        baz="BAZ",
    )


def test_execute_application__with_fast_mode(
    dummy_render_class,
    dummy_jobbergate_application_config,
    dummy_jobbergate_application_module,
    mocker,
):
    dummy_render_class.prepared_input = dict(
        foo="FOO",
        bar="BAR",
        baz="BAZ",
    )

    mocker.patch.object(importlib.import_module("inquirer.prompt"), "ConsoleRender", new=dummy_render_class)
    app_params = execute_application(
        dummy_jobbergate_application_module,
        dummy_jobbergate_application_config,
        fast_mode=True,
    )
    assert app_params == dict(
        foo="FOO",
        bar="BAR",
        baz="zab",  # Only 'baz' has a default value, so it should be used
    )
