import pathlib
import re

import snick
import pytest
import yaml

from jobbergate_cli.constants import JOBBERGATE_APPLICATION_MODULE_FILE_NAME, JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.subapps.applications.file_tools import validate_application_files, find_templates, dump_full_config


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


def test_find_templates(tmp_path):
    application_path = tmp_path / "dummy"
    assert list(find_templates(application_path)) == []

    application_path.mkdir()
    templates_path = application_path / "templates"
    templates_path.mkdir()
    file1 = templates_path / "file1"
    file1.write_text("foo")
    file2 = templates_path / "file2"
    file2.write_text("bar")
    dir1 = templates_path / "dir1"
    dir1.mkdir()
    file3 = dir1 / "file3"
    file3.write_text("baz")
    assert sorted(find_templates(application_path)) == [pathlib.Path(f"templates/file{i}") for i in (1, 2)]


def test_dump_full_config(tmp_path):
    application_path = tmp_path / "dummy"
    application_path.mkdir()
    templates_path = application_path / "templates"
    templates_path.mkdir()
    file1 = templates_path / "file1"
    file1.write_text("foo")
    file2 = templates_path / "file2"
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
        )
    )
