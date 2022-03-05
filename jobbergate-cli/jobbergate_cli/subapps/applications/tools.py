import ast
import copy
import importlib
import importlib.util
import json
import pathlib
import tarfile
import tempfile
from typing import Any, Dict, Iterator, List, Optional, Tuple, cast

from loguru import logger
import snick
import yaml

from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_CONFIG,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    TAR_NAME,
)
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.subapps.applications.questions import gather_config_values


def validate_application_files(application_path: pathlib.Path):
    """
    Validate application files at a given directory.

    Confirms:
        application_path exists
        application_path contains an application python module
        application_path contains an application configuration file
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


def find_templates(application_path: pathlib.Path) -> List[pathlib.Path]:
    """
    Finds templates in the application path.
    """
    template_root_path = application_path / "templates"
    if template_root_path.exists():
        return sorted(
            p.relative_to(application_path)
            for p in template_root_path.glob("**/*")
            if p.is_file()
        )
    else:
        return list()


def load_default_config() -> Dict[str, Any]:
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


def fetch_application_data(
    jg_ctx: JobbergateContext,
    id: Optional[int] = None,
    identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve an application from the API by ``id`` or ``identifier``.
    """
    url = f"/applications/{id}"
    params = dict()
    if id is None and identifier is None:
        raise Abort(
            """
            You must supply either [yellow]id[/yellow] or [yellow]identifier[/yellow].
            """,
            subject="INVALID PARAMS",
            warn_only=True,
        )
    elif id is not None and identifier is not None:
        raise Abort(
            """
            You may not supply both [yellow]id[/yellow] and [yellow]identifier[/yellow].
            """,
            subject="INVALID PARAMS",
            warn_only=True,
        )
    elif identifier is not None:
        url = f"/applications"
        params["identifier"] = identifier

    # Make static type checkers happy
    assert jg_ctx.client is not None

    stub = f"{id=}" if id is not None else f"{identifier=}"
    return cast(
        Dict[str, Any],
        make_request(
            jg_ctx.client,
            url,
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve application {stub} from API",
            support=True,
            params=params,
        ),
    )


def validate_application_data(app_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    with Abort.check_expressions(
        f"The application files fetched from the API were invalid",
        raise_kwargs=dict(
            subject="INVALID APPLICATION FILES",
            log_message=f"Application files retrieved from the API were invalid",
        ),
    ) as checker:
        app_module = app_data.get(JOBBERGATE_APPLICATION_MODULE_FILE_NAME)
        checker(
            app_module is not None,
            f"Application data does not contain {JOBBERGATE_APPLICATION_MODULE_FILE_NAME}",
        )
        if app_module is not None:
            try:
                ast.parse(app_module)
                is_valid_python = True
            except Exception:
                is_valid_python = False
            checker(is_valid_python, f"The application module from the API is not valid python code")

        app_config = app_data.get(JOBBERGATE_APPLICATION_CONFIG_FILE_NAME)
        checker(
            app_config is not None,
            f"Application data does not contain {JOBBERGATE_APPLICATION_CONFIG_FILE_NAME}",
        )
        if app_config is not None:
            try:
                app_config = yaml.safe_load(app_config)
                is_valid_yaml = True
            except Exception:
                is_valid_yaml = False
            checker(is_valid_yaml, f"The application config from the API is not valid YAML")

    # Make static type checkers happy
    app_module = cast(str, app_module)
    app_config = cast(Dict[str, Any], app_config)

    return (app_module, app_config)


def upload_application(
    jg_ctx: JobbergateContext,
    application_path: pathlib.Path,
    application_id: int,
) -> bool:
    """
    Upload an application given an application path and the application id.
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None

    with tempfile.TemporaryDirectory() as temp_dir_str:
        build_path = pathlib.Path(temp_dir_str)
        logger.debug("Building application tar file at {build_path}")
        tar_path = build_application_tarball(application_path, build_path)
        response_code = cast(
            int,
            make_request(
                jg_ctx.client,
                f"/applications/{application_id}/upload",
                "POST",
                expect_response=False,
                abort_message=f"Request to upload application files was not accepted by the API",
                support=True,
                files=dict(upload_file=open(tar_path, "rb")),
            ),
        )
        return response_code == 201


def import_from_text(app_module: str):
    """
    Import a python module from a text string by creating a temporary file and importing it with importlib.
    """
    with tempfile.NamedTemporaryFile(suffix=".py") as temp_module:
        temp_path = pathlib.Path(temp_module.name)
        temp_path.write_text(app_module)
        spec = importlib.util.spec_from_file_location("JobbergateApplication", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def execute_application(
    app_module: str,
    app_config: Dict[str, Any],
    supplied_params: Dict[str, Any],
    sbatch_params: Optional[List[Any]] = None,
    fast_mode: bool = False,
) -> Dict[str, Any]:
    """
    Execute the jobbergate application python module.
    """
    module = import_from_text(app_module)
    application = module.JobbergateApplication(app_config)
    gather_config_values(application, app_config, supplied_params, fast_mode=fast_mode)

    rendered_params = dict(param_dict=json.dumps(app_config))

    # Possibly overwrite script name
    job_script_name_from_param = app_config.get("job_script_name")
    if job_script_name_from_param:
        rendered_params["job_script_name"] = job_script_name_from_param

    if sbatch_params is not None:
        for (i, param) in enumerate(sbatch_params):
            rendered_params[f"sbatch_params_{i}"] = param
        rendered_params["sbatch_params_len"] = len(sbatch_params)

    return rendered_params
