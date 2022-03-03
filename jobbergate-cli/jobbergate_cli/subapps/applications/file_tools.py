import ast
import copy
import pathlib
import tarfile
import typing

import snick
import yaml

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    TAR_NAME,
)
from jobbergate_cli.exceptions import Abort


def validate_application_files(application_path: pathlib.Path):
    """
    Validate application files at a given directory.

    Confirms:
        application_path exists
        applicaiton_path contains an application python module
        applicaiton_path contains an application configuration file
    """
    with Abort.check_expressions(
        f"The application files in {application_path} were invalid",
        raise_kwargs=dict(
            subject="INVALID APPLICATION FILES",
            log_message=f"Application files located at {application_path} failed validation",
        ),
    ) as checker:
        checker(
            application_path.exists(),
            f"Application directory {application_path} does not exist",
        )

        application_module = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        checker(
            application_module.exists(),
            snick.unwrap(
                f"""
                Application directory does not contain required application module
                {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}
                """
            ),
        )
        try:
            ast.parse(application_module.read_text())
            is_valid_python = True
        except Exception:
            is_valid_python = False
        checker(is_valid_python, f"The application module at {application_module} is not valid python code")

        application_config = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        checker(
            application_config.exists(),
            snick.unwrap(
                f"""
                Application directory does not contain required configuration file
                {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}
                """
            ),
        )
        try:
            yaml.safe_load(application_config.read_text())
            is_valid_yaml = True
        except Exception:
            is_valid_yaml = False
        checker(is_valid_yaml, f"The application config at {application_config} is not valid YAML")


def find_templates(application_path: pathlib.Path) -> typing.Iterator[pathlib.Path]:
    """
    Finds templates in the application path.
    """
    template_root_path = application_path / "templates"
    if template_root_path.exists():
        for path in template_root_path.iterdir():
            if path.is_file():
                yield pathlib.Path("templates") / path.name


def load_default_config() -> typing.Dict[str, typing.Any]:
    """
    Load the default config for an application.
    """
    return copy.deepcopy(JOBBERGATE_APPLICATION_CONFIG)


def dump_full_config(application_path: pathlib.Path) -> str:
    """
    Dump the application config as text. Add existing template file paths into the config.
    """
    config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config = yaml.safe_load(config_path.read_text())
    config["jobbergate_config"]["template_files"] = sorted(str(t) for t in find_templates(application_path))
    return yaml.dump(config)


def read_application_module(application_path: pathlib.Path) -> str:
    """
    Read the text from the application module found in the supplied application path.
    """
    module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    return module_path.read_text()


def build_application_tarball(application_path: pathlib.Path, build_dir: pathlib.Path) -> pathlib.Path:
    # TODO: Need to test this next. Also verify the logic for adding files (skip all dirs but templates?)
    # with tempfile.TemporaryDirectory() as temp_dir:
    tar_path = build_dir / TAR_NAME
    with tarfile.open(str(tar_path), "w|gz") as archive:
        module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
        archive.add(module_path, arcname=f"/{module_path.name}")

        config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
        archive.add(config_path, arcname=f"/{config_path.name}")

        template_root_path = application_path / "templates"
        if template_root_path.exists():
            for template_path in template_root_path.iterdir():
                if template_path.is_file:
                    rel_path = template_path.relative_to(application_path)
                    archive.add(template_path, arcname=f"/{rel_path}")
    return tar_path
